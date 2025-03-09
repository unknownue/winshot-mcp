# Winshot MCP

一个为Cursor实现的Model-Client Protocol (MCP)窗口截图集成工具，允许Cursor的agent模式捕获和分析应用程序窗口。

## 概述

本项目实现了具有窗口截图功能的MCP协议，使大型语言模型(LLM)能够可视化观察和与应用程序UI交互。通过捕获特定窗口的截图，LLM可以更好地理解用户的环境并提供更具上下文感知的帮助。

## 特性

- 支持在Windows、macOS和Linux上列出所有活动窗口
- 捕获特定应用程序窗口的截图
- 通过MCP协议将窗口截图发送给LLM
- 与Cursor的agent模式集成

## 安装设置

1. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

2. 平台特定的要求:
   - Windows: `pip install pygetwindow`
   - Linux: `sudo apt-get install xdotool imagemagick`
   - macOS: 需要向终端/IDE授予屏幕录制权限
     - 首次运行时，系统会询问是否允许应用程序录制屏幕
     - 也可以在 系统设置 > 隐私与安全性 > 屏幕录制 中手动授权
     - 如果使用的是IDE（如VS Code），请确保为IDE授予权限

3. 运行窗口截图演示:
   ```
   python winshot_demo.py
   ```

## 在Cursor中使用

要在Cursor的agent模式中使用窗口截图功能:

1. 启动MCP服务器:
   ```
   python mcp_server.py
   ```

2. 在Cursor中，可以在agent模式下使用以下命令:
   - `list_windows()` - 列出所有可用窗口
   - `capture_window("Window Title")` - 捕获具有给定标题的窗口的截图
   - `capture_window(window_index)` - 通过索引捕获窗口的截图

## 项目结构

- `winshot.py`: 核心窗口截图功能
- `mcp_server.py`: 带有窗口截图支持的MCP服务器
- `mcp_client.py`: MCP客户端实现
- `cursor_mcp_adapter.py`: 连接Cursor与MCP的适配器
- `cursor_winshot.py`: Cursor特定的窗口截图集成
- `winshot_demo.py`: 展示窗口截图功能的演示脚本

## 演示

运行 `python winshot_demo.py` 将启动一个交互式演示，它会:
1. 列出系统上所有可用的窗口
2. 允许您选择要截图的窗口
3. 启动截图过程，**注意：当前版本可能需要您手动点击要截图的窗口**

截图过程中的交互提示是macOS安全机制的一部分，这确保了用户对屏幕捕获有控制权。截图保存在当前目录中，文件名以 `window_shot_` 开头。

## 截图问题排查

如果您在macOS上遇到截图问题:

1. 确认屏幕录制权限已授予给终端或IDE
2. **在截图过程中，当系统提示时，请点击您想要截图的窗口**
3. 尝试不同的截图方法：代码会自动尝试三种不同的方法
4. 对于无法自动捕获的窗口，可能需要修改 `winshot.py` 中的截图参数

### 已知限制

- **需要用户干预**：当前版本在macOS上可能需要用户手动点击窗口以完成截图。这是系统安全限制的结果，目前被认为是可接受的。
- 某些窗口可能无法通过ID定位，此时会尝试捕获前台窗口。
- 某些应用的窗口可能无法正确捕获，特别是那些使用非标准窗口管理的应用。

## 协议详情

该实现扩展了MCP协议，增加了窗口截图特定的消息类型:

- `window_list_request`/`window_list_response`: 用于列出可用窗口
- `window_screenshot_request`/`window_screenshot_response`: 用于捕获截图

有关完整的协议文档，请参阅 `mcp_protocol.md`。 