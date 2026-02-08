# X Articles - 详细指南

将 Markdown 文章发布到 X 文章编辑器，支持富文本格式和图片。

## 先决条件

- X Premium 订阅（发布文章需要）
- 安装 Google Chrome
- 安装 `bun`

## 用法

```bash
# 发布 markdown 文章（预览模式）
npx -y bun ${SKILL_DIR}/scripts/x-article.ts article.md

# 使用自定义封面图片
npx -y bun ${SKILL_DIR}/scripts/x-article.ts article.md --cover ./cover.jpg

# 实际发布
npx -y bun ${SKILL_DIR}/scripts/x-article.ts article.md --submit
```

## Markdown 格式

```markdown
---
title: My Article Title
cover_image: /path/to/cover.jpg
---

# Title (becomes article title)

Regular paragraph text with **bold** and *italic*.

## Section Header

More content here.

![Image alt text](./image.png)

- List item 1
- List item 2

1. Numbered item
2. Another item

> Blockquote text

[Link text](https://example.com)

\`\`\`
代码块会变成引用块（X 不支持代码）
\`\`\`
```

## Frontmatter 字段

| 字段 | 描述 |
|-------|-------------|
| `title` | 文章标题（或使用第一个 H1） |
| `cover_image` | 封面图片路径或 URL |
| `cover` | cover_image 的别名 |
| `image` | cover_image 的别名 |

## 图片处理

1.  **封面图片**: 第一张图片或 frontmatter 中的 `cover_image`
2.  **远程图片**: 自动下载到临时目录
3.  **占位符**: 内容中的图片使用 `XIMGPH_N` 格式
4.  **插入**: 找到占位符，选中并替换为实际图片

## Markdown 转 HTML 脚本

转换 markdown 并检查结构：

```bash
# 获取包含所有元数据的 JSON
npx -y bun ${SKILL_DIR}/scripts/md-to-html.ts article.md

# 仅输出 HTML
npx -y bun ${SKILL_DIR}/scripts/md-to-html.ts article.md --html-only

# 保存 HTML 到文件
npx -y bun ${SKILL_DIR}/scripts/md-to-html.ts article.md --save-html /tmp/article.html
```

JSON 输出:
```json
{
  "title": "Article Title",
  "coverImage": "/path/to/cover.jpg",
  "contentImages": [
    {
      "placeholder": "XIMGPH_1",
      "localPath": "/tmp/x-article-images/img.png",
      "blockIndex": 5
    }
  ],
  "html": "<p>Content...</p>",
  "totalBlocks": 20
}
```

## 支持的格式

| Markdown | HTML 输出 |
|----------|-------------|
| `# H1` | 仅标题（不在正文中） |
| `## H2` - `###### H6` | `<h2>` |
| `**bold**` | `<strong>` |
| `*italic*` | `<em>` |
| `[text](url)` | `<a href>` |
| `> quote` | `<blockquote>` |
| `` `code` `` | `<code>` |
| ```` ``` ```` | `<blockquote>` (X 限制) |
| `- item` | `<ul><li>` |
| `1. item` | `<ol><li>` |
| `![](img)` | 图片占位符 |

## 工作流

1.  **解析 Markdown**: 提取标题、封面、内容图片，生成 HTML
2.  **启动 Chrome**: 带有 CDP 的真实浏览器，持久登录
3.  **导航**: 打开 `x.com/compose/articles`
4.  **创建文章**: 如果在列表页面，点击创建按钮
5.  **上传封面**: 使用文件输入上传封面图片
6.  **填充标题**: 在标题字段中输入标题
7.  **粘贴内容**: 复制 HTML 到剪贴板，粘贴到编辑器
8.  **插入图片**: 对于每个占位符（倒序）：
    -   在编辑器中找到占位符文本
    -   选中占位符
    -   复制图片到剪贴板
    -   粘贴以替换选区
9.  **审查**: 浏览器保持打开 60s 用于预览
10. **发布**: 仅当使用 `--submit` 标志时

## 示例会话

```
User: /post-to-x article ./blog/my-post.md --cover ./thumbnail.png

Claude:
1. 解析 markdown: title="My Post", 3 张内容图片
2. 使用 CDP 启动 Chrome
3. 导航到 x.com/compose/articles
4. 点击创建按钮
5. 上传 thumbnail.png 作为封面
6. 填充标题 "My Post"
7. 粘贴 HTML 内容
8. 在占位符位置插入 3 张图片
9. 报告: "Article composed. Review and use --submit to publish."
```

## 故障排除

-   **无创建按钮**: 确保 X Premium 订阅有效
-   **封面上传失败**: 检查文件路径和格式 (PNG, JPEG)
-   **图片未插入**: 验证粘贴的内容中是否存在占位符
-   **内容未粘贴**: 检查 HTML 剪贴板: `npx -y bun ${SKILL_DIR}/scripts/copy-to-clipboard.ts html --file /tmp/test.html`

## 工作原理

1.  `md-to-html.ts` 将 Markdown 转换为 HTML:
    -   提取 frontmatter (标题, 封面)
    -   将 markdown 转换为 HTML
    -   用唯一占位符替换图片
    -   在本地下载远程图片
    -   返回结构化 JSON

2.  `x-article.ts` 通过 CDP 发布:
    -   启动真实 Chrome (绕过检测)
    -   使用持久配置文件 (保存的登录)
    -   通过 DOM 操作导航和填充编辑器
    -   从系统剪贴板粘贴 HTML
    -   查找/选择/替换每个图片占位符
