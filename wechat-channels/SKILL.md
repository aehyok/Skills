---
name: wechat-channels
description: >
  微信视频号（WeChat Channels / finder）数据查询与视频下载解密，基于本项目本地安装的 Glasser CLI（TikHub 与腾讯互选接口）。
  凡是涉及视频号的需求都用这个 skill：查某个视频号账号的主页资料、粉丝/获赞/作品数，拉作品列表和每条的点赞收藏转发评论，
  看评论、合集、直播回放和直播间在线人数，全站或号内搜视频号视频，查视频号达人的商单报价/预估 CPM/粉丝画像（腾讯互选），
  以及下载视频号视频（含解密）。用户说"视频号""微信视频""finder""sph 开头的号""weixin.qq.com/sph 链接""下载某某视频号最新视频"
  "看看这个视频号达人数据"时都要用，即使没提 Glasser。公众号文章类需求不在此列。
---

# 微信视频号（WeChat Channels）

本 skill 把"视频号查数据 + 下载视频"的完整链路固化下来。底层是 Glasser 付费接口，所以先遵守 Glasser 的规矩，再按下面的链路走。

## 前置约定

- **CLI 是本地安装**：在项目根目录（本 skill 往上三级，即 `.claude/skills/wechat-channels/../../..`）运行 `npx glasser …`，不要 `npm install -g`，也不要 `glasser skill install`。
- **Glasser 的通用规则见 `.claude/skills/glasser/SKILL.md`**：inspect 先于 run、报 Run 状态 + 数据商原话 + `Charge`、引用 `Run URL`、`--task` 贯穿同一件事、钱是精确小数字符串。下面只写视频号特有的部分。
- **花钱前说价**：单次 0.01 美元 级、且用户明确要的操作直接跑；翻页、批量、互选类（0.04 美元以上）先报单价和预计总价，等用户点头。原因：余额是用户的钱，空结果照样扣费。
- **输出落盘**：每次 run 都加 `-o <scratchpad>/runs/<名字>.json`，再用脚本或小段 Python 读取需要的字段，别把整个响应倒进上下文。
- **接口细节**（入参、输出字段、翻页字段、价格、已知坑）在 `references/endpoints.md`，需要时读对应小节。

## 第一步：拿到 finder username

几乎所有 TikHub 账号接口都要 `v2_…@finder` 格式的 username。按用户给的东西选路：

| 用户给的 | 怎么拿 username | 花费 |
|---|---|---|
| 昵称 | `fetch_search`，`business_type=account`，挑 `jumpInfo.userName` 以 `@finder` 结尾、标题与昵称一致的那项 | 0.01 美元 |
| sph 短号 | `fetch_channel_id_to_username` | 0.01 美元 |
| 分享链接 `weixin.qq.com/sph/…` | `fetch_video_detail` 传 `share_url`，顺便就拿到了这条视频 | 0.01 美元 |
| 之前会话里已经查到过 | 直接复用，别重复花钱 | 0 |

同名账号有多个时，列出昵称、认证信息、简介让用户选，不要猜。

## 第二步：按需求调用

常见需求 → 接口（都在 `references/endpoints.md` 第 2/3 节有详情）：

- 账号概况 → `fetch_user_profile`（粉丝、作品、获赞、收藏、转发、关联公众号）；认证主体 → `fetch_channel_info`
- 作品列表和互动数据 → `fetch_user_videos`（一页约 15 条，翻页靠 `last_buffer` / `up_continue`）。列表开头可能是**置顶的旧视频**，"最新"要按 `create_time` 排序判断（下载脚本的 `--latest` 已经这样做），展示给用户时也按时间排，并标出置顶项
- 单条视频 → `fetch_video_detail`；评论 → `fetch_video_comments`
- 合集 → `fetch_user_collections` → `fetch_collection_videos`
- 直播 → `fetch_live_history`（回放可下载）/ `fetch_live_detail`（在线人数）
- 找视频 → 全站 `fetch_search_videos`，号内 `fetch_search_channel_videos`
- 商单评估（报价、预估 CPM、粉丝画像、播放量、商单视频）→ 腾讯互选三件套 `/channels-creator-search` → `-detail` / `-videos`，provider 是 `wechat`。只覆盖入驻互选的达人，查不到要如实说明。

调用模板（版本号以 inspect 打印的 run 命令为准）：

```sh
npx glasser inspect -p tikhub -e /api/v1/wechat_channels/v2/fetch_user_videos --task <task>
npx glasser run -p tikhub -e /api/v1/wechat_channels/v2/fetch_user_videos \
  -i '{"username":"v2_…@finder","raw":false}' --task <task> -o <scratchpad>/runs/ch_videos.json
```

TikHub 偶发 `HTTP 400 请求失败，请重试`（`PROVIDER_ERROR 0.00 美元`，不扣费）：原样再跑一次（新 Idempotency-Key），仍失败再报告。

## 第三步：下载视频

视频号视频是加密的：文件前 128 KiB 与 `decode_key` 生成的 ISAAC64 密钥流做了异或。打包好的脚本一步完成"下载 → 解密 → 校验"：

```sh
S=.claude/skills/wechat-channels/scripts/wx_channels.py
python3 -I $S list <run.json>                                   # 看有哪些、序号、是否可下载
python3 -I $S download <run.json> --out downloads --latest 1    # 最新 1 条
python3 -I $S download <run.json> --out downloads --index 1,2,4 # 指定序号
python3 -I $S download <run.json> --out downloads --title 关键词
```

- `<run.json>` 可以是 `fetch_user_videos` / `fetch_collection_videos` / `fetch_live_history` / `fetch_video_detail` 任一个 `raw=false` 的 `-o` 输出。
- 文件名自动为 `昵称_YYYYMMDD_标题.mp4`，默认存到项目的 `downloads/`。
- 脚本每条输出一行 JSON：`ok`、文件路径、大小、ffprobe 的时长/分辨率/是否有音轨。解密以 MP4 `ftyp` 头校验，失败会报错而不是留下坏文件。
- **链接和 `decode_key` 必须来自同一次响应**，且链接会过期。所以下载紧跟在 run 之后；隔了很久或报 403/解密失败，就重新 run 一次拿新链接再下。
- 用旧响应里的链接重下不花钱，能用就先用。

下载后告诉用户：文件位置、时长、分辨率、大小；说明拿到的是压缩版（实测 720p/576p，非 `file_size` 标的原画）。

## 汇报格式

每次涉及付费调用，回复里都要有：
1. 结果本身（表格优先：日期、标题、点赞/收藏/转发/评论等）
2. 本次花费合计，以及每个 Run 的链接（`Run URL`）
3. 数据缺口要直说（如播放量为 0 是接口限制，不是真的没人看）
4. 下一步可选项及价格

## 版权提醒

下载他人视频用于学习、分析、竞品参考可以；提醒用户未经授权二次发布或搬运剪辑会侵权，尤其是商单场景。提一句即可，不要说教。
