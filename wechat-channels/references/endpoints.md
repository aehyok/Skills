# 视频号接口参考（Glasser 目录，2026-11 核对）

价格和版本会变，运行前一律 `npx glasser inspect -p <provider> -e <endpoint>` 以 inspect 结果为准。
下文字段路径均指 `raw=false`（精简）输出，TikHub 接口统一建议传 `"raw": false`。

## 目录
1. ID 体系与获取链路
2. TikHub 接口（公开数据，约 $0.01/次）
3. 腾讯互选接口（商单数据，$0.04–0.12/次）
4. 已知坑

## 1. ID 体系与获取链路

| ID | 样子 | 用途 | 从哪拿 |
|---|---|---|---|
| finder username | `v2_…@finder` | 几乎所有账号级 TikHub 接口的入参 | 综合搜索 `jumpInfo.userName`；作品对象的 `username`；`fetch_channel_id_to_username` |
| 视频号 ID | `sph…` 短号 | 用户能在 App 里看到的号 | `fetch_channel_info` 的 `channel_id` |
| object_id | 纯数字（64 位，按字符串处理） | 单条作品：详情 / 评论 / 分享链接 | 作品列表的 `id` |
| export_id | `export/…` | 搜索结果里的作品 ID（会过期） | 搜索结果 `exportId` |
| topic_id | 纯数字 | 合集 | `fetch_user_collections` |
| live_id | 纯数字 | 直播间 | 直播回放条目 |
| appId（互选） | 互选平台 ID | 互选三个接口 | `/channels-creator-search` 结果 |

**只有昵称时**：`tikhub /api/v1/wechat_search/v2/fetch_search`，`{"keyword":"<昵称>","business_type":"account","raw":false}`。
结果混有公众号和视频号：取 `data.items[]` 里 `jumpInfo.userName` 以 `@finder` 结尾的那一项（公众号那项是 `gh_…`）。核对 `title`（去掉 `<em>` 高亮）与昵称一致；同名多个时列出让用户选。

**只有 sph 短号时**：`/api/v1/wechat_channels/v2/fetch_channel_id_to_username`，`{"channel_id":"sph…"}` → `data.username`。

**只有分享链接时**（`https://weixin.qq.com/sph/…`）：`fetch_video_detail` 传 `share_url`，响应里的 `username` 即作者。

## 2. TikHub 接口（provider `tikhub`）

路径前缀 `/api/v1/wechat_channels/v2/`，搜索类在 `/api/v1/wechat_search/v2/`。

### 账号
| 接口 | 入参 | 关键输出 |
|---|---|---|
| `fetch_user_profile` | `username` | `nickname` `signature` `region`(IP属地) `fans_count` `feeds_count` `like_count` `fav_count` `forward_count` `friend_follow_count` `live_duration_hours` `collection_count` `verify_desc` `linked_accounts[]`(关联公众号) |
| `fetch_channel_info` | `username` | `channel_id`(sph) `info{视频号ID, IP归属地, 服务单位, 主体类型, 服务类别, 认证时间…}` |
| `fetch_user_collections` | `username` | `collections[]{topic_id, name, desc, feed_count, topic_type}` |

### 作品
| 接口 | 入参 | 关键输出 / 翻页 |
|---|---|---|
| `fetch_user_videos` | `username`, `last_buffer`(翻页) | `videos[]`；`up_continue` 为真时把 `last_buffer` 传回取下一页 |
| `fetch_video_detail` | 三选一：`object_id` > `export_id`(+`object_nonce_id`) > `share_url` | 单个视频对象 |
| `fetch_collection_videos` | `topic_id`，可选 `topic` `username` `topic_type`(默认16) `last_buffer` | `videos[]` `total_count`；`down_continue` 翻页 |
| `fetch_video_comments` | `object_id`，可选 `comment_id`(展开二级回复) `last_buffer` | `comments[]{content, nickname, like_count, reply_count, create_time, ip_region}`；`down_continue` 翻页 |
| `fetch_video_share_url` | `object_id` | `share_url` |

视频对象字段：`id` `object_nonce_id` `username` `nickname` `title` `description` `create_time` `like_count` `fav_count` `forward_count` `comment_count` `read_count` `media{full_url, url, url_token, decode_key, duration, width, height, file_size, md5, cover_url}`。

### 直播
| 接口 | 入参 | 关键输出 |
|---|---|---|
| `fetch_live_history` | `username`，可选 `last_buffer` `flag` | `lives[]`（结构同视频对象，可下载）`total_count`；`continue_flag` 翻页 |
| `fetch_live_detail` | `live_id`，可选 `finder_username` | `live_status`(1直播中/2已结束) `online_count` `max_online_count` `replay_watch_uv` `replay_url` |

### 搜索
| 接口 | 入参 | 说明 |
|---|---|---|
| `/api/v1/wechat_search/v2/fetch_search_videos` | `keyword`，可选 `duration`(all/short/medium/long) `sort`(default/latest/hot) `publish_time`(all/day/week/half_year) `cursor` | 全站搜视频号视频。结果只有 `exportId`，下载需再走 `fetch_video_detail(export_id=…)` |
| `fetch_search_channel_videos` | `username` `keyword`，可选 `cursor` | 号内搜索；`continue_flag`/`next_cursor` 翻页 |
| `/api/v1/wechat_search/v2/fetch_search` | `keyword` `business_type` | 综合搜索，`business_type=account` 用来找账号 |

## 3. 腾讯互选接口（provider `wechat`，数据来自 justoneapi）

只覆盖入驻腾讯互选的达人；搜不到不代表账号不存在。

| 接口 | 价格 | 入参 | 输出 |
|---|---|---|---|
| `/channels-creator-search` | $0.0738 | `keyword`, `page`(从1) | 每页约 30 个：`appid` `nickname` `fans_num_level` 类目 `city_label` `avg_read_count` `avg_like_count` `median_read_count` `tags` |
| `/channels-creator-detail` | $0.04428 | `appId` | 上述 + `expected_cpm` `interaction_rate`；`user_profile` 粉丝画像（年龄/性别/设备/地域/省份/手机品牌/兴趣）；`near_videos` 近期播放 |
| `/channels-creator-videos` | $0.0738 | `appId` `beginDate` `endDate`(yyyyMMdd)，可选 `videoType`(ALL/ORDER商单/HOT/PERSON) `page` | `video_list[]{release_time, description, read_pv, read_uv, comment_pv, fav_pv, heart_pv, share_pv, interaction_rate, video_type}` |

互选返回临时 `COLLECT FAILED` 不扣费，可重试。

## 4. 已知坑（实测）

- TikHub `fetch_user_videos` 的 `read_count`（播放量）实测全为 0；要播放数据用互选 `/channels-creator-videos`（仅互选达人）。
- `fans_count` 等对部分账号返回 0，文档自己承认。实测机构号（虎嗅APP）`fans_count` `like_count` `fav_count` `forward_count` 全为 0，`region` 显示为海外地名；作品数、直播时长、合集数正常。
- `fetch_user_videos` 列表前几条可能是置顶的旧视频（实测虎嗅前 3 条是 2025–2026 年初的置顶），不能把第 0 条当最新。
- 偶发 `HTTP 400 请求失败，请重试`，计费为 `PROVIDER_ERROR $0.00`：用新 Idempotency-Key 重跑一次即可（CLI 不传 key 时自动生成新的）。
- 下载链接给的是压缩版（实测 720p 或 576p），`media.file_size` 是原画大小，与下载到的文件大小对不上属正常。
- 每次请求返回新的 `full_url` + `decode_key`，必须同一次响应里的配对使用；链接会过期（实测 10 分钟内仍可用），拿到尽快下。
- 64 位 ID（`id` `object_id` `topic_id` `live_id`）一律按字符串传，别经过浮点。
- 一页条数由微信决定（实测作品列表一页 15 条），不能指定。
