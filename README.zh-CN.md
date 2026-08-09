# MoHan Desktop Assistant / 墨寒桌面语音互动虚拟助手

<p align="center">
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml"><img alt="Windows CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/windows-ci.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml"><img alt="Cross-platform core CI" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/cross-platform-core.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml"><img alt="CodeQL" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/codeql.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml"><img alt="Python Security Audit" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/security-audit.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml"><img alt="Extended Secret Defense / Gitleaks" src="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/actions/workflows/secret-defense.yml/badge.svg"></a>
  <a href="https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases"><img alt="Latest Release" src="https://img.shields.io/github/v/release/hitoshic1982/MoHan-PC-Desktop-Assistant?include_prereleases&label=release"></a>
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.15" src="https://img.shields.io/badge/Python-3.15-3776AB.svg?logo=python&logoColor=white">
  <img alt="4 interface languages" src="https://img.shields.io/badge/interface_languages-4-79648d.svg">
</p>

[繁體中文與 English](README.md) · [日本語](README.ja.md) · [快速开始](QUICKSTART.md) ·
[路线图](ROADMAP.md) · [参与贡献](CONTRIBUTING.md) ·
[安全说明](SECURITY.md)

> 准备发布的预览版本：v2.3.0 RC1（`v2.3.0-rc.1`）<br>
> Windows 10/11 · Python 3.15 · PySide6 · MIT License

墨寒是一款重视安全、隐私与角色连续感的 Windows 桌面虚拟助手。她以来自
北宋、寄宿于赤焰剑中的千年女剑魂为角色背景，结合透明桌面角色、文字与
语音互动、长期记忆、工作管理、权限控制工具，以及可扩展的云端与智能家居
连接架构。

> **跨平台进度：** Windows 仍是唯一完成真机、完整回归、安装与发布验证的
> 平台。macOS／Linux 目前只建立安全的平台边界，并通过三系统 CI 检查核心
> 导入、纯核心逻辑与 Qt offscreen。`v2.3.0-rc.N` 发布线还会提供可启动、
> 可切换四语但功能受限的 DMG／AppImage Preview；CI 不能代替真机兼容性或
> 完整功能验证。详情请见
> [跨平台状态与能力矩阵](docs/CROSS-PLATFORM.md)。

> 本项目遵循[炎剑开源软件家族质量标准](PUBLISHING.md)。

![墨寒桌面助手主视觉](docs/media/mohan-hero.png)

## 最新实机界面

以下图片与繁中、英文、日文 README 共用同一组最新版媒体文件，确保界面改版
后不会出现不同语言各自停留在旧截图的问题。

<table>
  <tr>
    <td width="50%" align="center"><a href="docs/media/first-run-wizard.png"><img src="docs/media/first-run-wizard.png" alt="墨寒首次启动设置向导"></a><br><strong>首次启动设置向导</strong></td>
    <td width="50%" align="center"><a href="docs/media/voice-modes.png"><img src="docs/media/voice-modes.png" alt="Realtime 与标准语音模式"></a><br><strong>Realtime 与标准语音</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/expressions.png"><img src="docs/media/expressions.png" alt="墨寒表情与动作系统"></a><br><strong>表情与动作系统</strong></td>
    <td width="50%" align="center"><a href="docs/media/tasks-and-ideas.png"><img src="docs/media/tasks-and-ideas.png" alt="墨寒待办事项与创作灵感"></a><br><strong>待办事项与创作灵感</strong></td>
  </tr>
  <tr>
    <td width="50%" align="center"><a href="docs/media/long-term-memory.png"><img src="docs/media/long-term-memory.png" alt="墨寒可编辑长期记忆"></a><br><strong>可编辑长期记忆</strong></td>
    <td width="50%" align="center"><a href="docs/media/security-permissions.png"><img src="docs/media/security-permissions.png" alt="墨寒权限与安全设置"></a><br><strong>权限与安全设置</strong></td>
  </tr>
</table>

## 创作者的话

作者 CHOU MING HUA 是一位来自台湾、43 岁且原本没有程序设计背景的父亲。
这个项目来自二十多年来对 AI 虚拟伴侣与《电脑情人梦》的憧憬，并与 Codex
协作投入近 50 小时，将墨寒从想象一步步做成真正能在 Windows 上运行的
开源软件。

炎剑文化工作室对开源的理解，不是把第一个“能运行”的版本交给世界，再把
细节留给别人收拾。为了让墨寒说话时仍像同一个人，我们为托腮、倚靠与正面
姿势分别制作闭嘴、展唇、窄唇与圆唇画面，再把声音切成细小时间片，反复校准
元音、过渡速度与结束时机。陪伴感往往不是由某一项庞大功能产生，而是来自
她开口、眨眼与停顿时，那些没有破坏真实感的细节。

<p align="center">
  <a href="docs/media/creation-viseme-development.webp"><img src="docs/media/creation-viseme-development.webp" width="100%" alt="墨寒三种姿势与四种语音口型的整齐开发图版"></a>
</p>
<p align="center"><sub>三种姿势、同一套口型规格：让每一次开口都维持角色连续性。</sub></p>

开发过程中不够自然的画面也会被留下来检查。眼白中的一个亮点、闭眼时残留
的线条、被拉扯的嘴角，或只有几个像素的边界，都可能让使用者在一瞬间觉得
“她不像刚才的墨寒”。因此，问题会被标出、局部对比、修复，再通过回归测试
确认眼睛、嘴角与脸部其他区域没有被连带破坏。

<p align="center">
  <a href="docs/media/creation-frame-by-frame-qa.webp"><img src="docs/media/creation-frame-by-frame-qa.webp" width="100%" alt="墨寒眼睛与口型逐帧检查及干净验证画面"></a>
</p>
<p align="center"><sub>把瑕疵标出来，再用干净画面与自动测试共同验收；几个像素也值得认真。</sub></p>

这份认真不是为了把作品包装成从未犯错，而是因为我们真的想完成一个梦想。
开源对炎剑而言，是先尽力修好自己能看见的问题，再公开方法、代码与失败后
的经验，邀请世界一起把它锻造得更好。**剑，我已铸成；余下的路，就交给
你们了。**

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
- 可插拔语音供应器基础；Realtime 或云端不可用时优先回退到 Windows 本地女声。
- 可选的 Azure Speech 女性声线预览；用户自备密钥与区域，由 Windows 分开加密，失败时立即回退到 Windows 本地女声。
- 本机保存的对话、可编辑长期记忆、待办事项、创作灵感、工作计时与提醒。
- 工作、陪伴、勿扰、会议、离席与休眠模式。
- 具有风险分级、确认、双重确认、允许列表、审计与紧急停止的电脑工具。
- 可在 Windows 电脑之间转移工作进度的 `.mohan-profile` 文件。

## 简体中文支持范围

`v2.1.0-rc.1` 提供简体中文最小可用范围，包括：

- 首次启动设置向导。
- 对话、语音、电脑权限、基本设置页签与主要按钮。
- 完整简体中文墨寒人格提示词。
- 简体中文离线回复、工作模式台词与内置提醒词。
- `zh-CN` 普通话转录设置与同语系女性 Windows 声音优先选择。
- 在繁中、简中、英文与日语之间切换内置默认提醒，同时保留用户自定义内容。

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

Azure Speech 为默认关闭的预览供应器，只列出 Microsoft 官方标示为女性的
繁中、简中、英文与日语声线。它需要用户自己的 Azure Speech 资源密钥与相符区域；
设定不完整时不会发出网络请求，服务失败时会立即回退到 Windows 女性本地
语音。真实 Azure 帐号完成端到端试播前，不会宣称为稳定整合。

## 下载与安装

1. 前往 [GitHub Releases](../../releases)。
2. 下载最新的 `Windows-x64.zip` 与对应的 `SHA256.txt`。
3. 核对 SHA-256，并完整解压 ZIP。
4. 运行 `MoHan-Desktop-Assistant-2.3.0-rc.1.exe`。
5. 在首次设置向导选择“简体中文（中国大陆）”。
6. 请保持 EXE、`_internal` 与 `assets` 在同一程序文件夹内。

未经数字签名的开源预览版本可能触发 Windows SmartScreen。请确认下载来源并
核对 SHA-256 后再运行。

`v2.3.0-rc.N` 发布线另提供 macOS Apple Silicon（arm64）与 Intel（x86_64）
`.dmg`（各内含对应 `.app`），以及 Linux x86_64 `.AppImage`。它们是
**功能受限 Preview**，只开放启动画面、四语说明、平台
数据路径与安全停用边界，并不等同 Windows 完整版。语音、透明桌面角色、完整
聊天与工作界面、云端连接器、系统工具、自动启动和秘密输入仍保持停用，等待
真机验证。请先阅读 [Preview 安装包说明](docs/PREVIEW-PACKAGES.md)。

### 自动化发布边界

只有不可变的 `v2.3.0-rc.N` 标签可以发布此系列。Windows ZIP／EXE／MSI、
macOS Apple Silicon／Intel 双架构 DMG 与 Linux AppImage 必须先在各自原生
CI 完成成品启动验证，才会进入
同一个 GitHub 预发布版。Pull Request 只保留短期测试产物，不会建立 Release。
正式发布文件同时包含 SHA256SUMS、分别通过 CycloneDX 1.7 官方结构／授权／
依赖图验证的 Windows／Preview SBOM、去识别化 Tachyon 性能证据与摘要、
Windows 更新清单、Artifact Attestation 与完整四语 Release 说明。

## OpenAI API

云端 AI、OpenAI 语音与 Realtime 功能需要用户自己的 OpenAI API 密钥、
Project 权限与 API 额度。ChatGPT Plus 订阅不包含 API 额度。

从 `v2.1.0-rc.1` 起，文字聊天默认使用较新的 `gpt-5.6-luna`，设置清单不再
提供 `gpt-5.4-mini`。现有 mini 设置会自动迁移到 Luna，用户主动选择的其他
模型不会被覆盖。

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

需求：Windows 10/11、Python 3.15.0rc1。
升级、数据保留与回退方式请见
[Python 3.15 迁移说明](docs/PYTHON-3.15-MIGRATION.md)。

```powershell
py -3.15 -m venv .venv
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
