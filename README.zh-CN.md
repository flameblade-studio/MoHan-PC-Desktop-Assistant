# MoHan Desktop Assistant / 墨寒桌面语音互动虚拟助手

[繁體中文與 English](README.md) · [快速开始](QUICKSTART.md) ·
[路线图](ROADMAP.md) · [参与贡献](CONTRIBUTING.md) ·
[安全说明](SECURITY.md)

> 当前公开预览版本：v2.0.14 RC3<br>
> Windows 10/11 · Python 3.12 · PySide6 · MIT License

墨寒是一款重视安全、隐私与角色连续感的 Windows 桌面虚拟助手。她以来自
北宋、寄宿于赤焰剑中的千年女剑魂为角色背景，结合透明桌面角色、文字与
语音互动、长期记忆、工作管理、权限控制工具，以及可扩展的云端与智能家居
连接架构。

![墨寒桌面助手主视觉](docs/media/mohan-hero.png)

## 创作者的话

作者 CHOU MING HUA 是一位来自台湾、43 岁且原本没有程序设计背景的父亲。
这个项目来自二十多年来对 AI 虚拟伴侣与《电脑情人梦》的憧憬，并与 Codex
协作投入近 50 小时，将墨寒从想象一步步做成真正能在 Windows 上运行的
开源软件。

墨寒采用 MIT License。欢迎工程师通过
[Issue](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues)
与 [Pull Request](https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/pulls)
参与语音、动画、表情、工具、智能家居与本地化开发。

## 主要功能

- 透明、无边框的桌面半身角色，可固定在任务栏上方。
- 呼吸、眨眼、鼠标注视、脸部视差、头发、衣袖、饰品与身体微转向。
- 具有情境优先级、冷却与去重机制的表情仲裁器。
- AIUEO 元音嘴型、辅音嘴型、音频驱动开合与语音结束强制闭嘴。
- 文字聊天、单次麦克风、OpenAI Realtime 与 Windows 本机语音。
- 本机保存的对话、可编辑长期记忆、待办事项、创作灵感、工作计时与提醒。
- 工作、陪伴、勿扰、会议、离席与休眠模式。
- 具有风险分级、确认、双重确认、允许列表、审计与紧急停止的电脑工具。
- 可在 Windows 电脑之间转移工作进度的 `.mohan-profile` 文件。

## 简体中文支持范围

RC3 提供简体中文最小可用范围，包括：

- 首次启动设置向导。
- 对话、语音、电脑权限、基本设置页签与主要按钮。
- 完整简体中文墨寒人格提示词。
- 简体中文离线回复、工作模式台词与内置提醒词。
- `zh-CN` 普通话转录设置与同语系女性 Windows 声音优先选择。
- 在繁中、简中与英文之间切换内置默认提醒，同时保留用户自定义内容。

更高级的管理页面仍可能显示部分台湾繁体中文。保存界面语言后，请重新启动
墨寒以完整应用；当前版本不提供免重启的界面热切换。

## Windows 本机语音

新用户默认使用 Windows 本机语音，因此没有 OpenAI API 密钥也能先体验
基本朗读与离线功能。

声音列表只显示 Windows 明确标示为女性的已安装声音。`zh-CN` 会优先选择
中国大陆中文语系的女性声音；如果系统没有合格声音，墨寒不会悄悄改用可能
为男性的系统默认声音，而会显示明确提示。用户可通过 Windows 语言与语音
设置安装额外语音包。

台湾繁中模式仍优先使用 Microsoft Yating，不会因简中支持而改变。

## 下载与安装

1. 前往 [GitHub Releases](../../releases)。
2. 下载最新的 `Windows-x64.zip` 与对应的 `SHA256.txt`。
3. 核对 SHA-256，并完整解压 ZIP。
4. 运行 `MoHan-Desktop-Assistant-2.0.14-rc.3.exe`。
5. 在首次设置向导选择“简体中文（中国大陆）”。
6. 请保持 EXE、`_internal` 与 `assets` 在同一程序文件夹内。

未经数字签名的开源预览版本可能触发 Windows SmartScreen。请确认下载来源并
核对 SHA-256 后再运行。

## OpenAI API

云端 AI、OpenAI 语音与 Realtime 功能需要用户自己的 OpenAI API 密钥、
Project 权限与 API 额度。ChatGPT Plus 订阅不包含 API 额度。

没有 API 密钥时，本机数据管理、离线人格回复、工作提醒与 Windows 本机语音
仍然可用，但不会具有完整云端 AI 能力。请勿将 API 密钥写入源代码、Issue、
截图或 Git。

在线功能的实际可用性取决于用户所在地、网络环境、服务条款、账号、Project
权限与模型供应情况。本项目不会承诺第三方在线服务在所有地区都可访问。

## 安全与隐私

- 对话、长期记忆、待办与工作记录默认保存在用户自己的 Windows 电脑。
- API 密钥、OAuth 凭据与 Home Assistant Token 使用 Windows DPAPI 分开
  加密保存，不写入 SQLite 数据库。
- 对话内容不能自行扩大墨寒的电脑操作权限。
- 删除、覆盖、发送、发布或高风险设备操作必须遵守本机权限与确认流程。
- 可携配置文件不会包含 API 密钥、OAuth Token、机器权限或远程设备密钥。

## 集成验证状态

Microsoft、GitHub 与 Home Assistant 的架构、权限边界与内部测试已经建立，
但仍未完成所有真实账号、仓库、服务器与实体设备的端到端验证。这些功能属于
实验性预览集成，默认关闭。请先使用非关键账号、测试仓库与低风险设备验证。

Google Gmail、Calendar 与 Drive 已完成当前项目的真实连接测试，但每位用户
仍必须建立并授权自己的 Google OAuth 应用程序。

## 从源代码运行

需求：Windows 10/11、Python 3.12+。

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

运行测试与公开内容审计：

```powershell
python tests\run_all.py
python tools\audit_public_release.py
```

## 许可证与贡献

本项目采用 [MIT License](LICENSE)。贡献前请阅读
[CONTRIBUTING.md](CONTRIBUTING.md) 与 [SECURITY.md](SECURITY.md)。

墨寒不仅是一套功能集合，也是一项长期创作。欢迎尊重角色连续性、安全边界、
用户隐私与测试标准的开发者共同参与。
