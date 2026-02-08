---
name: baoyu-post-to-x
description: 将内容和文章发布到 X (Twitter)。支持带图片/视频的常规推文和 X 文章（长篇 Markdown）。通过真实的 Chrome CDP 绕过自动化检测。当用户提到 "post to X", "tweet", "publish to Twitter", 或 "share on X" 时使用。
---

# 发布到 X (Twitter)

通过真实的 Chrome 浏览器将文本、图片、视频和长篇文章发布到 X（绕过反机器人检测）。

## 脚本目录

**重要**: 所有脚本都位于此技能的 `scripts/` 子目录中。

**Agent 执行说明**:
1. 确定此 SKILL.md 文件的目录路径为 `SKILL_DIR`
2. 脚本路径 = `${SKILL_DIR}/scripts/<script-name>.ts`
3. 将本文档中的所有 `${SKILL_DIR}` 替换为实际路径

**脚本参考**:
| 脚本 | 用途 |
|--------|---------|
| `scripts/x-browser.ts` | 常规推文（文本 + 图片） |
| `scripts/x-video.ts` | 视频推文（文本 + 视频） |
| `scripts/x-quote.ts` | 带评论的引用推文 |
| `scripts/x-article.ts` | 长篇文章发布 (Markdown) |
| `scripts/md-to-html.ts` | Markdown → HTML 转换 |
| `scripts/copy-to-clipboard.ts` | 复制内容到剪贴板 |
| `scripts/paste-from-clipboard.ts` | 发送真实的粘贴按键 |

## 首选项 (EXTEND.md)

使用 Bash 检查 EXTEND.md 是否存在（优先级顺序）：

```bash
# 首先检查项目级别
test -f .baoyu-skills/baoyu-post-to-x/EXTEND.md && echo "project"

# 然后检查用户级别（跨平台：$HOME 适用于 macOS/Linux/WSL）
test -f "$HOME/.baoyu-skills/baoyu-post-to-x/EXTEND.md" && echo "user"
```

┌──────────────────────────────────────────────────┬───────────────────┐
│                       路径                       │       位置        │
├──────────────────────────────────────────────────┼───────────────────┤
│ .baoyu-skills/baoyu-post-to-x/EXTEND.md          │ 项目目录          │
├──────────────────────────────────────────────────┼───────────────────┤
│ $HOME/.baoyu-skills/baoyu-post-to-x/EXTEND.md    │ 用户主目录        │
└──────────────────────────────────────────────────┴───────────────────┘

┌───────────┬───────────────────────────────────────────────────────────────────────────┐
│   结果    │                                   动作                                    │
├───────────┼───────────────────────────────────────────────────────────────────────────┤
│ 找到      │ 读取、解析、应用设置                                                      │
├───────────┼───────────────────────────────────────────────────────────────────────────┤
│ 未找到    │ 使用默认值                                                                │
└───────────┴───────────────────────────────────────────────────────────────────────────┘

**EXTEND.md 支持**: 默认 Chrome 配置文件 | 自动提交首选项

## 先决条件

- Google Chrome 或 Chromium
- `bun` 运行时
- 首次运行: 手动登录 X（会话将保存）

## 参考

- **常规推文**: 参见 `references/regular-posts.md` 获取手动工作流、故障排除和技术细节
- **X 文章**: 参见 `references/articles.md` 获取长篇文章发布指南

---

## 常规推文

文本 + 最多 4 张图片。

```bash
npx -y bun ${SKILL_DIR}/scripts/x-browser.ts "Hello!" --image ./photo.png          # 预览
npx -y bun ${SKILL_DIR}/scripts/x-browser.ts "Hello!" --image ./photo.png --submit  # 发布
```

**参数**:
| 参数 | 描述 |
|-----------|-------------|
| `<text>` | 推文内容（位置参数） |
| `--image <path>` | 图片文件（可重复，最多 4 张） |
| `--submit` | 发布（默认：预览） |
| `--profile <dir>` | 自定义 Chrome 配置文件 |

---

## 视频推文

文本 + 视频文件。

```bash
npx -y bun ${SKILL_DIR}/scripts/x-video.ts "Check this out!" --video ./clip.mp4          # 预览
npx -y bun ${SKILL_DIR}/scripts/x-video.ts "Amazing content" --video ./demo.mp4 --submit  # 发布
```

**参数**:
| 参数 | 描述 |
|-----------|-------------|
| `<text>` | 推文内容（位置参数） |
| `--video <path>` | 视频文件 (MP4, MOV, WebM) |
| `--submit` | 发布（默认：预览） |
| `--profile <dir>` | 自定义 Chrome 配置文件 |

**限制**: 常规用户最长 140s，Premium 用户最长 60min。处理时间：30-60s。

---

## 引用推文

带评论的引用现有推文。

```bash
npx -y bun ${SKILL_DIR}/scripts/x-quote.ts https://x.com/user/status/123 "Great insight!"          # 预览
npx -y bun ${SKILL_DIR}/scripts/x-quote.ts https://x.com/user/status/123 "I agree!" --submit       # 发布
```

**参数**:
| 参数 | 描述 |
|-----------|-------------|
| `<tweet-url>` | 引用的 URL（位置参数） |
| `<comment>` | 评论文本（位置参数，可选） |
| `--submit` | 发布（默认：预览） |
| `--profile <dir>` | 自定义 Chrome 配置文件 |

---

## X 文章

长篇 Markdown 文章（需要 X Premium）。

```bash
npx -y bun ${SKILL_DIR}/scripts/x-article.ts article.md                        # 预览
npx -y bun ${SKILL_DIR}/scripts/x-article.ts article.md --cover ./cover.jpg    # 带封面
npx -y bun ${SKILL_DIR}/scripts/x-article.ts article.md --submit               # 发布
```

**参数**:
| 参数 | 描述 |
|-----------|-------------|
| `<markdown>` | Markdown 文件（位置参数） |
| `--cover <path>` | 封面图片 |
| `--title <text>` | 覆盖标题 |
| `--submit` | 发布（默认：预览） |

**Frontmatter**: YAML front matter 中支持 `title`, `cover_image`。

---

## 注意事项

- 首次运行: 需要手动登录（会话持久化）
- 始终在 `--submit` 之前进行预览
- 跨平台: macOS, Linux, Windows

## 扩展支持

通过 EXTEND.md 自定义配置。有关路径和支持的选项，请参见 **首选项** 部分。

