---
name: wechat-video-downloader
description: Download videos embedded in WeChat Official Account articles. Use when the user provides an mp.weixin.qq.com article URL and asks to download, extract, analyze, or save embedded mpvideo/wxv videos, or when the user provides a wxv_ video id from a WeChat article and wants the actual mp4 file.
---

# WeChat Video Downloader

## Quick Start

Use `scripts/download_wechat_videos.py` from this skill directory.

Typical commands (macOS / Linux; on Windows use `python` and the same forward-slash paths also work):

```bash
python3 skills/wechat-video-downloader/scripts/download_wechat_videos.py "https://mp.weixin.qq.com/s/..." --output downloads/wechat
python3 skills/wechat-video-downloader/scripts/download_wechat_videos.py "https://mp.weixin.qq.com/s/..." --vid wxv_4537390665495953415 --output downloads/wechat
```

The script prints JSON with discovered videos, resolved mp4 URLs, and downloaded file paths.

## Workflow

1. Run the script with the article URL.
2. If the user gave a specific `wxv_...` id, pass it with `--vid`.
3. Save outputs in a project-local directory such as `downloads/wechat` unless the user requested another path.
4. Verify downloads with `ffprobe` when available, especially if the file is unexpectedly small.

## How It Works

The script:

- Fetches the article HTML and extracts `wxv_...` ids, titles, covers, and article parameters.
- Tries WeChat's `get_mp_video_play_url` endpoint first.
- Falls back to Selenium + local Chrome/Edge performance logs, because WeChat often exposes the real `mpvideo.qpic.cn/*.mp4` links only during page runtime.
- Downloads the matching mp4 URLs with browser-like headers.

## Requirements

- Python with `requests`.
- For the runtime fallback: `selenium` and installed Chrome or Edge. Install with `pip install requests selenium`.
- Chrome/Edge is auto-detected in standard Windows, macOS (`/Applications`), and Linux (`PATH`) locations. For a non-standard install, set `CHROME_BIN` to the browser executable.
- `ffprobe` is optional and only needed for extra validation.

If Selenium or a browser is unavailable, report that direct API resolution failed and browser runtime capture is required.

## Notes

- WeChat mp4 URLs are temporary signed links. Download them immediately after resolving.
- Do not rely on article HTML containing direct `.mp4` URLs; most articles only contain `mpvideo` containers and `wxv_...` ids.
- If multiple videos are present and the user did not specify one, download all discovered videos.
