# Regular Posts - Detailed Guide

发布文本和图片到 X 的详细文档。

## 手动工作流

如果你喜欢逐步控制：

### 步骤 1: 复制图片到剪贴板

```bash
npx -y bun ${SKILL_DIR}/scripts/copy-to-clipboard.ts image /path/to/image.png
```

### 步骤 2: 从剪贴板粘贴

```bash
# 简单的粘贴到最前端的应用程序
npx -y bun ${SKILL_DIR}/scripts/paste-from-clipboard.ts

# 粘贴到 Chrome 并重试
npx -y bun ${SKILL_DIR}/scripts/paste-from-clipboard.ts --app "Google Chrome" --retries 5

# 以较短的延迟快速粘贴
npx -y bun ${SKILL_DIR}/scripts/paste-from-clipboard.ts --delay 200
```

### 步骤 3: 使用 Playwright MCP (如果 Chrome 会话可用)

```bash
# 导航
mcp__playwright__browser_navigate url="https://x.com/compose/post"

# 获取元素引用
mcp__playwright__browser_snapshot

# 输入文本
mcp__playwright__browser_click element="editor" ref="<ref>"
mcp__playwright__browser_type element="editor" ref="<ref>" text="Your content"

# 粘贴图片 (复制到剪贴板后)
mcp__playwright__browser_press_key key="Meta+v"  # macOS
# 或者
mcp__playwright__browser_press_key key="Control+v"  # Windows/Linux

# 截图以验证
mcp__playwright__browser_take_screenshot filename="preview.png"
```

## 图片支持

- 格式: PNG, JPEG, GIF, WebP
- 每条推文最多 4 张图片
- 图片复制到系统剪贴板，然后通过快捷键粘贴

## 示例会话

```
User: /post-to-x "Hello from Claude!" --image ./screenshot.png

Claude:
1. 运行: npx -y bun ${SKILL_DIR}/scripts/x-browser.ts "Hello from Claude!" --image ./screenshot.png
2. Chrome 打开 X 撰写页面
3. 文本输入到编辑器
4. 图片复制到剪贴板并粘贴
5. 浏览器保持打开 30s 用于预览
6. 报告: "Post composed. Use --submit to post."
```

## 故障排除

- **找不到 Chrome**: 设置 `X_BROWSER_CHROME_PATH` 环境变量
- **未登录**: 首次运行打开 Chrome - 手动登录，Cookie 会被保存
- **图片粘贴失败**:
  - 验证剪贴板脚本: `npx -y bun ${SKILL_DIR}/scripts/copy-to-clipboard.ts image <path>`
  - 在 macOS 上，在系统设置 > 隐私与安全性 > 辅助功能中授予 Terminal/iTerm "辅助功能" 权限
  - 在粘贴操作期间保持 Chrome 窗口可见并置于顶层
- **osascript 权限被拒绝**: 在系统偏好设置中授予 Terminal 辅助功能权限
- **速率限制**: 等待几分钟后重试

## 工作原理

`x-browser.ts` 脚本使用 Chrome DevTools Protocol (CDP) 来：
1. 启动真实 Chrome (不是 Playwright) 带有 `--disable-blink-features=AutomationControlled`
2. 使用持久配置文件目录保存登录会话
3. 通过 CDP 命令与 X 交互 (Runtime.evaluate, Input.dispatchKeyEvent)
4. **使用 osascript 粘贴图片** (macOS): 发送真实的 Cmd+V 按键到 Chrome，绕过 X 可能检测到的 CDP 合成事件

这种方法绕过了 X 用于阻止 Playwright/Puppeteer 的反自动化检测。

### 图片粘贴机制 (macOS)

CDP 的 `Input.dispatchKeyEvent` 发送网站可以检测到的“合成”键盘事件。X 忽略出于安全考虑的合成粘贴事件。解决方案：

1. 通过 Swift/AppKit 将图片复制到系统剪贴板 (`copy-to-clipboard.ts`)
2. 通过 `osascript` 将 Chrome 置于顶层
3. 通过 `osascript` 和 System Events 发送真实的 Cmd+V 按键
4. 等待上传完成

这需要 Terminal 在系统设置中拥有“辅助功能”权限。

