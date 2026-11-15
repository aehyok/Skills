# Skills

个人整理的 Claude Code / Agent Skills 合集，每个目录是一个独立的 skill（入口为 `SKILL.md`）。

| Skill | 用途 |
| --- | --- |
| [wechat-video-downloader](./wechat-video-downloader) | 下载微信公众号文章里内嵌的视频 |
| [wechat-channels](./wechat-channels) | 微信视频号数据查询与视频下载解密 |

## wechat-video-downloader

给一个 `mp.weixin.qq.com` 公众号文章链接，自动找出文章里嵌入的所有视频（`wxv_…`）并下载为 mp4。

**功能**

- 解析文章 HTML，提取视频 id、标题，以及封面和宽高比（文章结构不同时可能取不到）
- 先调用微信 `get_mp_video_play_url` 接口直接拿播放地址
- 接口拿不到时，用 Selenium + 本机 Chrome/Edge 无头打开页面，从网络日志里抓取真实的 `mpvideo.qpic.cn/*.mp4` 地址
- 带浏览器请求头下载，可选用 `ffprobe` 校验时长、分辨率、音轨
- 支持 `--vid` 只下载指定视频、`--list-only` 只列出视频

**用法**

```bash
pip install requests selenium   # selenium 仅浏览器兜底时需要

python3 wechat-video-downloader/scripts/download_wechat_videos.py \
  "https://mp.weixin.qq.com/s/..." --output downloads/wechat --ffprobe
```

输出为 JSON，包含发现的视频、解析出的 mp4 地址和下载文件路径。Chrome/Edge 会在 Windows、macOS、Linux 的常见位置自动检测，装在非标准位置时设置 `CHROME_BIN`。

> 微信的 mp4 链接是带签名的临时地址，解析后需立即下载。

## wechat-channels

微信视频号（WeChat Channels / finder）一站式能力，底层基于本地安装的 Glasser CLI（`npx glasser`） 调用 TikHub 与腾讯互选接口（付费接口，按次计费）。

**功能**

- **定位账号**：通过昵称、sph 短号或 `weixin.qq.com/sph/…` 分享链接拿到 finder username
- **账号数据**：主页资料、粉丝 / 获赞 / 作品数、认证主体、关联公众号
- **作品数据**：作品列表及每条的点赞、收藏、转发、评论，单条详情与评论
- **合集与直播**：合集视频、直播回放、直播间在线人数
- **搜索**：全站搜视频号视频，或在某个号内搜索
- **商单评估**：通过腾讯互选查达人报价、预估 CPM、粉丝画像、商单视频
- **视频下载解密**：视频号视频前 128 KiB 经 ISAAC64 密钥流异或加密，脚本一步完成下载、解密和 MP4 头校验

**下载用法**

```bash
S=wechat-channels/scripts/wx_channels.py
python3 -I $S list <run.json>                                   # 查看可下载的视频及序号
python3 -I $S download <run.json> --out downloads --latest 1    # 最新 1 条
python3 -I $S download <run.json> --out downloads --index 1,2,4 # 按序号
python3 -I $S download <run.json> --out downloads --title 关键词 # 按标题
```

`<run.json>` 为 Glasser 作品列表、合集、直播回放或视频详情接口的输出。文件名自动生成为 `昵称_YYYYMMDD_标题.mp4`。接口细节见 [`references/endpoints.md`](./wechat-channels/references/endpoints.md)。

> 视频链接与 `decode_key` 必须来自同一次响应且会过期，下载需紧跟查询之后。

## 版权说明

下载的视频仅供个人学习、分析参考，未经授权请勿二次发布或搬运。
