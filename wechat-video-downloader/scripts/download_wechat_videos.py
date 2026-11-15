#!/usr/bin/env python
"""Download mpvideo/wxv videos embedded in WeChat Official Account articles."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

import requests


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch_text(url: str) -> tuple[str, dict[str, str]]:
    session = requests.Session()
    response = session.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text, session.cookies.get_dict()


def article_params(url: str, text: str) -> dict[str, str]:
    parsed = parse_qs(urlparse(url.replace("&amp;", "&")).query)
    params = {
        "biz": parsed.get("__biz", [""])[0],
        "mid": parsed.get("mid", [""])[0],
        "idx": parsed.get("idx", ["1"])[0],
    }
    for source, key in [("biz", "biz"), ("mid", "mid"), ("idx", "idx")]:
        if params.get(key):
            continue
        match = re.search(rf'var\s+{source}\s*=\s*["\']([^"\']+)["\']', text)
        if match:
            params[key] = html.unescape(match.group(1))
    return params


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def extract_title(text: str) -> str:
    patterns = [
        r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)',
        r'var\s+msg_title\s*=\s*["\']([^"\']+)',
        r'<h1[^>]*id=["\']activity-name["\'][^>]*>(.*?)</h1>',
        r"<title>(.*?)</title>",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            return clean_text(match.group(1))
    return "wechat-article"


def context_title(text: str, pos: int) -> str:
    before = text[max(0, pos - 3500) : pos]
    # Prefer nearby styled headings/strong text.
    candidates = re.findall(r"<(?:h[1-4]|strong|span|p)[^>]*>(.{1,180}?)</(?:h[1-4]|strong|span|p)>", before, re.I | re.S)
    for candidate in reversed(candidates[-20:]):
        cleaned = clean_text(candidate)
        if 2 <= len(cleaned) <= 80 and not cleaned.startswith("http"):
            return cleaned
    return ""


def discover_videos(text: str) -> list[dict[str, Any]]:
    videos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in re.finditer(r"wxv_\d{10,}", text):
        vid = match.group(0)
        if vid in seen:
            continue
        seen.add(vid)
        window = text[max(0, match.start() - 1200) : min(len(text), match.end() + 1200)]
        cover_match = re.search(r'data-cover=["\']([^"\']+)', window)
        ratio_match = re.search(r'data-ratio=["\']([^"\']+)', window)
        title = context_title(text, match.start())
        videos.append(
            {
                "index": len(videos) + 1,
                "vid": vid,
                "title": title or f"video-{len(videos) + 1}",
                "cover": unquote(html.unescape(cover_match.group(1))) if cover_match else "",
                "ratio": ratio_match.group(1) if ratio_match else "",
            }
        )
    return videos


def try_direct_api(article_url: str, params: dict[str, str], vid: str) -> dict[str, Any]:
    biz = params.get("biz", "")
    mid = params.get("mid", "")
    idx = params.get("idx", "1") or "1"
    variants = [
        f"https://mp.weixin.qq.com/mp/videoplayer?action=get_mp_video_play_url&preview=0&vid={vid}",
        (
            "https://mp.weixin.qq.com/mp/videoplayer?action=get_mp_video_play_url&preview=0"
            f"&__biz={quote(biz)}&mid={mid}&idx={idx}&vid={vid}"
            "&ish265=true&uin=&key=&pass_ticket=&wxtoken=777&devicetype="
            "&clientversion=&appmsg_token=&x5=0&f=json"
        ),
    ]
    for api_url in variants:
        try:
            response = requests.get(
                api_url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Referer": article_url,
                    "Accept": "application/json,text/javascript,*/*;q=0.01",
                },
                timeout=20,
            )
            data = response.json()
        except Exception:
            continue
        result: dict[str, Any] = {
            "title": data.get("video_title") or "",
            "video_md5": data.get("video_md5") or "",
            "vidsn": data.get("vidsn") or "",
        }
        for item in data.get("url_info") or []:
            url = item.get("url")
            if url and ".mp4" in url:
                result["mp4_url"] = html.unescape(url)
                return result
        if any(result.values()):
            return result
    return {}


def browser_binary() -> str | None:
    candidates = [
        os.environ.get("CHROME_BIN"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    for name in ["chrome", "google-chrome", "google-chrome-stable", "msedge", "microsoft-edge", "chromium", "chromium-browser"]:
        found = shutil.which(name)
        if found:
            return found
    return None


def capture_runtime_urls(article_url: str, wait_seconds: int = 14) -> dict[str, str]:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except Exception as exc:
        raise RuntimeError("selenium is required for browser runtime capture") from exc

    binary = browser_binary()
    if not binary:
        raise RuntimeError("Chrome or Edge was not found")

    options = Options()
    options.binary_location = binary
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_argument("--window-size=1280,2200")
    options.add_argument(f"user-agent={USER_AGENT}")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.get(article_url)
        time.sleep(6)
        # Force lazy video containers into view so WeChat initializes media URLs.
        driver.execute_script(
            """
            const nodes = [...document.querySelectorAll('[data-mpvid]')];
            for (const node of nodes) {
              node.scrollIntoView({block: 'center'});
              node.click();
            }
            """
        )
        time.sleep(wait_seconds)
        logs = driver.get_log("performance")
    finally:
        driver.quit()

    urls: dict[str, str] = {}
    for entry in logs:
        try:
            message = json.loads(entry["message"])["message"]
        except Exception:
            continue
        params = message.get("params", {})
        request = params.get("request", {})
        response = params.get("response", {})
        url = request.get("url") or response.get("url") or ""
        if "mpvideo.qpic.cn" not in url or ".mp4" not in url:
            continue
        match = re.search(r"[?&]vid=(wxv_\d+)", url)
        if match and match.group(1) not in urls:
            urls[match.group(1)] = html.unescape(url)
    return urls


def safe_filename(value: str, fallback: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value or "")
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value or fallback)[:110]


def download(url: str, output: Path, referer: str) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(
        url,
        stream=True,
        timeout=90,
        headers={"User-Agent": USER_AGENT, "Referer": referer},
    ) as response:
        response.raise_for_status()
        total = 0
        with output.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    handle.write(chunk)
                    total += len(chunk)
    if total < 1024:
        raise RuntimeError(f"downloaded file is too small: {total} bytes")
    return total


def ffprobe(path: Path) -> str | None:
    if not shutil.which("ffprobe"):
        return None
    result = subprocess.run(
        ["ffprobe", "-hide_banner", "-i", str(path)],
        capture_output=True,
        timeout=20,
    )
    output = result.stderr or result.stdout
    return output.decode("utf-8", errors="replace").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article_url", help="mp.weixin.qq.com article URL")
    parser.add_argument("--vid", action="append", help="Download only this wxv_ id. Can be repeated.")
    parser.add_argument("--output", default="downloads/wechat", help="Output directory")
    parser.add_argument("--no-browser", action="store_true", help="Do not use Selenium browser fallback")
    parser.add_argument("--list-only", action="store_true", help="Only list discovered videos")
    parser.add_argument("--wait", type=int, default=14, help="Seconds to wait during browser capture")
    parser.add_argument("--ffprobe", action="store_true", help="Run ffprobe on downloaded files when available")
    args = parser.parse_args()

    article_html, _cookies = fetch_text(args.article_url)
    params = article_params(args.article_url, article_html)
    article_title = extract_title(article_html)
    videos = discover_videos(article_html)
    wanted = set(args.vid or [])
    if wanted:
        videos = [video for video in videos if video["vid"] in wanted]

    result: dict[str, Any] = {
        "article_url": args.article_url,
        "article_title": article_title,
        "count": len(videos),
        "videos": videos,
        "downloads": [],
        "errors": [],
    }

    if args.list_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    resolved: dict[str, str] = {}
    for video in videos:
        direct = try_direct_api(args.article_url, params, video["vid"])
        if direct.get("title") and video.get("title", "").startswith("video-"):
            video["title"] = direct["title"]
        if direct.get("video_md5"):
            video["video_md5"] = direct["video_md5"]
        if direct.get("vidsn"):
            video["vidsn"] = direct["vidsn"]
        if direct.get("mp4_url"):
            resolved[video["vid"]] = direct["mp4_url"]

    missing = [video["vid"] for video in videos if video["vid"] not in resolved]
    if missing and not args.no_browser:
        try:
            resolved.update(capture_runtime_urls(args.article_url, args.wait))
        except Exception as exc:
            result["errors"].append(f"browser capture failed: {exc}")

    output_dir = Path(args.output)
    for video in videos:
        vid = video["vid"]
        mp4_url = resolved.get(vid)
        video["mp4_url"] = mp4_url or ""
        if not mp4_url:
            result["errors"].append(f"no mp4 url resolved for {vid}")
            continue
        name = safe_filename(f"{video['index']:02d}-{video.get('title')}-{vid}", vid) + ".mp4"
        path = output_dir / name
        try:
            size = download(mp4_url, path, args.article_url)
            entry: dict[str, Any] = {"vid": vid, "path": str(path.resolve()), "bytes": size}
            if args.ffprobe:
                entry["ffprobe"] = ffprobe(path)
            result["downloads"].append(entry)
        except Exception as exc:
            result["errors"].append(f"download failed for {vid}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] and not result["downloads"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
