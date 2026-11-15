"""WeChat Channels (视频号) helper: list videos from a Glasser/TikHub run output, download and decrypt them.

Works on the `-o` output file of any raw=false TikHub endpoint that returns video objects:
fetch_user_videos / fetch_collection_videos (data.videos[]), fetch_live_history (data.lives[]),
fetch_video_detail (data is the single video).

usage:
  python3 -I wx_channels.py list <run.json>
  python3 -I wx_channels.py download <run.json> --out DIR [--latest N | --index 0,2 | --title 关键词]
  python3 -I wx_channels.py decrypt <encrypted.mp4> <decode_key> <out.mp4>

Videos are encrypted: the first 128 KiB is XORed with an ISAAC64 keystream seeded by decode_key.
The download URL and decode_key must come from the same API response, and the URL expires,
so download soon after the run.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

M = (1 << 64) - 1
ENC_LEN = 131072
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class Isaac64:
    def __init__(self, seed):
        self.rsl = [0] * 256
        self.rsl[0] = seed & M
        self.mm = [0] * 256
        self.aa = self.bb = self.cc = 0
        self._init()

    @staticmethod
    def _mix(s):
        a, b, c, d, e, f, g, h = s
        a = (a - e) & M; f ^= h >> 9; h = (h + a) & M
        b = (b - f) & M; g ^= (a << 9) & M; a = (a + b) & M
        c = (c - g) & M; h ^= b >> 23; b = (b + c) & M
        d = (d - h) & M; a ^= (c << 15) & M; c = (c + d) & M
        e = (e - a) & M; b ^= d >> 14; d = (d + e) & M
        f = (f - b) & M; c ^= (e << 20) & M; e = (e + f) & M
        g = (g - c) & M; d ^= f >> 17; f = (f + g) & M
        h = (h - d) & M; e ^= (g << 14) & M; g = (g + h) & M
        return [a, b, c, d, e, f, g, h]

    def _init(self):
        s = [0x9E3779B97F4A7C13] * 8
        for _ in range(4):
            s = self._mix(s)
        for src in (self.rsl, self.mm):
            for i in range(0, 256, 8):
                s = [(s[j] + src[i + j]) & M for j in range(8)]
                s = self._mix(s)
                self.mm[i:i + 8] = s
        self._generate()
        self.cnt = 256

    def _generate(self):
        mm, r = self.mm, self.rsl
        a = self.aa
        self.cc = (self.cc + 1) & M
        b = (self.bb + self.cc) & M
        for i in range(256):
            x = mm[i]
            k = i & 3
            if k == 0:
                mix = ~(a ^ ((a << 21) & M)) & M
            elif k == 1:
                mix = a ^ (a >> 5)
            elif k == 2:
                mix = a ^ ((a << 12) & M)
            else:
                mix = a ^ (a >> 33)
            a = (mix + mm[(i + 128) & 255]) & M
            y = (mm[(x >> 3) & 255] + a + b) & M
            mm[i] = y
            b = (mm[(y >> 11) & 255] + x) & M
            r[i] = b
        self.aa, self.bb = a, b

    def next(self):
        if self.cnt == 0:
            self._generate()
            self.cnt = 256
        self.cnt -= 1
        return self.rsl[self.cnt]


def keystream(seed, order):
    rng = Isaac64(seed)
    out = bytearray()
    while len(out) < ENC_LEN:
        out += rng.next().to_bytes(8, order)
    return bytes(out[:ENC_LEN])


def decrypt_file(path, key):
    """Decrypt the file's encrypted head in place. Returns the keystream byte order that produced an ftyp box."""
    with open(path, "r+b") as f:
        head = f.read(ENC_LEN)
        for order in ("big", "little"):
            plain = bytes(d ^ k for d, k in zip(head, keystream(int(key), order)))
            if plain[4:8] == b"ftyp":
                f.seek(0)
                f.write(plain)
                return order
    if head[4:8] == b"ftyp":
        return "plain"
    raise ValueError("no keystream variant produced an MP4 ftyp header (wrong decode_key or URL/key from different responses?)")


def load_videos(path):
    data = json.load(open(path, encoding="utf-8"))
    data = data.get("data", data)
    for k in ("videos", "lives"):
        if isinstance(data.get(k), list):
            return data, data[k]
    if isinstance(data.get("media"), dict):
        return data, [data]
    raise ValueError("no video objects found; use raw=false output of fetch_user_videos / fetch_collection_videos / fetch_live_history / fetch_video_detail")


def media_of(v):
    m = v.get("media")
    if isinstance(m, list):
        m = m[0] if m else None
    return m or {}


def date_of(v):
    ts = int(v.get("create_time") or 0)
    return datetime.datetime.fromtimestamp(ts).strftime("%Y%m%d") if ts else "nodate"


def title_of(v):
    t = (v.get("title") or v.get("short_title") or v.get("description") or "").strip().splitlines()
    return t[0] if t else ""


def safe_name(s, limit=60):
    s = re.sub(r"#\S+", "", s)
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", s).strip(" ._")
    return s[:limit] or "untitled"


def ffprobe(path):
    if not shutil.which("ffprobe"):
        return None
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", path],
        capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        return {"error": r.stderr.strip()[:200]}
    j = json.loads(r.stdout)
    vs = [s for s in j.get("streams", []) if s.get("codec_type") == "video"]
    return {
        "duration_s": round(float(j.get("format", {}).get("duration", 0)), 1),
        "resolution": f"{vs[0].get('width')}x{vs[0].get('height')}" if vs else None,
        "has_audio": any(s.get("codec_type") == "audio" for s in j.get("streams", [])),
    }


def cmd_list(a):
    _, videos = load_videos(a.run_json)
    for i, v in enumerate(videos):
        m = media_of(v)
        print(f"[{i}] {date_of(v)} | {title_of(v)[:40]} | like {v.get('like_count')} fav {v.get('fav_count')} "
              f"fwd {v.get('forward_count')} cmt {v.get('comment_count')} | {m.get('duration')}s "
              f"{m.get('width')}x{m.get('height')} | downloadable={'yes' if m.get('full_url') and m.get('decode_key') else 'no'}")


def select(videos, a):
    idx = list(range(len(videos)))
    if a.index:
        idx = [int(x) for x in a.index.split(",")]
    elif a.title:
        idx = [i for i, v in enumerate(videos) if a.title in title_of(v)]
    elif a.latest:
        idx = sorted(idx, key=lambda i: -int(videos[i].get("create_time") or 0))[: a.latest]
    return idx


def cmd_download(a):
    data, videos = load_videos(a.run_json)
    os.makedirs(a.out, exist_ok=True)
    results = []
    for i in select(videos, a):
        v = videos[i]
        m = media_of(v)
        url, key = m.get("full_url") or ((m.get("url") or "") + (m.get("url_token") or "")), m.get("decode_key")
        nick = safe_name(v.get("nickname") or data.get("nickname") or "wx", 30)
        dst = os.path.join(a.out, f"{nick}_{date_of(v)}_{safe_name(title_of(v))}.mp4")
        rec = {"index": i, "title": title_of(v), "file": dst}
        try:
            if not url or not key:
                raise ValueError("video object has no media url / decode_key")
            part = dst + ".part"
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r, open(part, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            rec["keystream"] = decrypt_file(part, key)
            os.replace(part, dst)
            rec["size_mb"] = round(os.path.getsize(dst) / 1048576, 1)
            rec["probe"] = ffprobe(dst)
            rec["ok"] = True
        except Exception as e:  # report per video, keep going with the rest
            rec["ok"] = False
            rec["error"] = f"{type(e).__name__}: {e}"
            if os.path.exists(dst + ".part"):
                os.remove(dst + ".part")
        results.append(rec)
        print(json.dumps(rec, ensure_ascii=False))
    ok = sum(r["ok"] for r in results)
    print(f"done: {ok}/{len(results)} ok")
    sys.exit(0 if ok == len(results) else 1)


def cmd_decrypt(a):
    shutil.copyfile(a.src, a.dst)
    try:
        order = decrypt_file(a.dst, a.key)
    except ValueError:
        os.remove(a.dst)
        raise
    print("ok: keystream byte order =", order, "->", a.dst)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list"); s.add_argument("run_json"); s.set_defaults(fn=cmd_list)
    s = sub.add_parser("download"); s.add_argument("run_json"); s.add_argument("--out", required=True)
    g = s.add_mutually_exclusive_group()
    g.add_argument("--latest", type=int); g.add_argument("--index"); g.add_argument("--title")
    s.set_defaults(fn=cmd_download)
    s = sub.add_parser("decrypt"); s.add_argument("src"); s.add_argument("key"); s.add_argument("dst"); s.set_defaults(fn=cmd_decrypt)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
