<div align="center">

<img src="./src/assets/icon.png" alt="MTools Logo" width="128" height="128">

# MTools
*一款功能强大、界面精美的现代化桌面工具集*

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Flet](https://img.shields.io/badge/Flet-0.28.3-brightgreen.svg)](https://flet.dev/)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()



集成图片处理、音视频编辑、AI 智能工具、开发辅助等功能，支持跨平台GPU加速

[快速开始](#-快速开始) · [功能特性](#-核心特性) · [界面预览](#-界面预览) · [下载发布版](https://github.com/HG-ha/MTools/releases)

</div>

---

## 🎨 界面预览

### 🌈 多主题支持

<table>
  <tr>
    <td align="center"><b>浅色模式</b></td>
    <td align="center"><b>深色模式</b></td>
  </tr>
  <tr>
    <td><img src="./assets/Light_Image_View.png" alt="浅色模式" width="400"/></td>
    <td><img src="./assets/Dark_Image_View.png" alt="深色模式" width="400"/></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><b>自定义背景模式</b></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="./assets/Custom_background_Image_View.png" alt="自定义背景" width="600"/></td>
  </tr>
</table>

### 📸 功能模块展示

<details>
<summary><b>🖼️ 图片处理工具</b> - 点击展开</summary>

<br/>

<table>
  <tr>
    <td align="center">浅色模式</td>
    <td align="center">深色模式</td>
  </tr>
  <tr>
    <td><img src="./assets/Light_Image_View.png" alt="图片工具-浅色" width="400"/></td>
    <td><img src="./assets/Dark_Image_View.png" alt="图片工具-深色" width="400"/></td>
  </tr>
</table>

**功能包括：**
- AI 智能抠图（背景移除）
- 专业压缩（mozjpeg + pngquant）
- 格式转换（12+ 种格式）
- 图片拼接（九宫格、横向、纵向）
- 尺寸调整、裁剪、旋转、水印
- 二维码生成、GIF 调整

</details>

<details>
<summary><b>🎬 音视频处理</b> - 点击展开</summary>

<br/>

<table>
  <tr>
    <td align="center">浅色模式</td>
    <td align="center">深色模式</td>
  </tr>
  <tr>
    <td><img src="./assets/Light_Media_View.png" alt="音视频工具-浅色" width="400"/></td>
    <td><img src="./assets/Dark_Media_View.png" alt="音视频工具-深色" width="400"/></td>
  </tr>
</table>

**功能包括：**
- AI 人声分离（UVR MDX-Net）
- 视频格式转换（MP4/AVI/MKV/MOV）
- 视频压缩（H.264/H.265）
- 音频格式转换（MP3/WAV/FLAC/AAC）
- 提取音轨、视频修复
- 速度调整、添加水印

</details>

<details>
<summary><b>🛠️ 开发工具</b> - 点击展开</summary>

<br/>

<table>
  <tr>
    <td align="center">浅色模式</td>
    <td align="center">深色模式</td>
  </tr>
  <tr>
    <td><img src="./assets/Light_DevTool_View.png" alt="开发工具-浅色" width="400"/></td>
    <td><img src="./assets/Dark_DevTool_View.png" alt="开发工具-深色" width="400"/></td>
  </tr>
</table>

**功能包括：**
- 编码转换（自动检测，解决乱码）
- Base64 转换（图片 ↔ Base64）
- JSON/XML/SQL 格式化
- 代码美化与验证

</details>

<details>
<summary><b>⚙️ 设置中心</b> - 点击展开</summary>

<br/>

<table>
  <tr>
    <td align="center">浅色模式</td>
    <td align="center">深色模式</td>
  </tr>
  <tr>
    <td><img src="./assets/Light_Setting_View.png" alt="设置-浅色" width="400"/></td>
    <td><img src="./assets/Dark_Setting_View.png" alt="设置-深色" width="400"/></td>
  </tr>
</table>

**设置选项：**
- 主题切换（浅色/深色/自动）
- 自定义主题色和字体
- GPU 加速配置
- 工具下载管理
- 性能优化选项

</details>

---

## ✨ 核心特性

### 🤖 AI 智能处理

- **🎨 AI 智能抠图** - 一键移除图片背景，支持人像、动漫、通用场景等多种模型，GPU 加速提速 3-10 倍
- **🎵 AI 人声分离** - 专业级人声/伴奏分离，支持 UVR MDX-Net 模型，轻松制作卡拉OK伴奏
- **🎬 视频人声分离** - 直接处理视频，分离人声或背景音，保留原画面

### 📷 图片工具箱

- **格式转换 & 压缩** - 支持 12+ 种格式，集成 mozjpeg、pngquant 专业引擎
- **智能编辑** - 尺寸调整、裁剪、旋转、水印、去除 EXIF
- **创意拼接** - 九宫格、单图切分、横向/纵向拼接
- **实用工具** - 二维码生成、GIF 调整、信息查看

### 🎬 音视频处理

- **格式转换** - 支持主流音视频格式互转（MP3/WAV/FLAC/MP4/AVI/MKV...）
- **智能压缩** - H.264/H.265 编码，自定义比特率和质量
- **速度调整** - 音视频加速/减速，不改变音调
- **提取 & 合成** - 提取音轨、添加水印、视频修复

### 🛠️ 开发辅助

- **编码转换** - 自动检测文件编码，一键解决乱码问题
- **Base64 工具** - 图片与 Base64 互转
- **代码格式化** - JSON/XML/SQL 美化与验证

---

## 🚀 快速开始

### 📦 方式一：下载发布版（推荐）

直接下载已编译好的可执行文件，**无需安装 Python**：

- **[Releases 下载](https://github.com/HG-ha/MTools/releases)**
- **[国内用户下载](https://openlist.wer.plus/MTools)**

支持平台：
- ✅ Windows 10/11 (x64)
- ⚠️ macOS (实验性支持)
- ⚠️ Linux (实验性支持)

下载后解压即可使用！

### 💻 方式二：从源码运行

#### 环境要求
- **操作系统**: Windows 10/11、macOS 或 Linux
- **Python**: 3.11+
- **包管理器**: [uv](https://github.com/astral-sh/uv) - 推荐使用的 Python 包管理器

#### 一键安装依赖

```bash
# 1. 克隆仓库
git clone https://github.com/HG-ha/MTools.git
cd MTools

# 2. 一键同步依赖（自动创建虚拟环境）
uv sync

# 3. 运行程序
uv run flet run
```

启用 CUDA GPU 加速（默认已启用平台通用加速）：

```bash
# 使用此方式可完全榨干NVIDIA GPU性能
# 替换为 GPU 版本（需要 NVIDIA GPU 和 CUDA 环境）
uv remove onnxruntime-directml onnxruntime
uv add onnxruntime-gpu==1.22.0
# 需要免去配置cuda和cudnn环境的话请更改为此依赖
# 会导致体积增大数倍
# uv add onnxruntime-gpu[cuda,cudnn]==1.22.0
```

---

## 📦 打包编译

如需将项目编译为独立的可执行文件（无需 Python 环境即可运行）：

📘 **[完整编译指南](./docs/build_guide.md)**

### 快速编译

```bash
# Release 模式（生产环境，无控制台）
python build.py

# Dev 模式（开发测试，保留控制台）
python build.py --mode dev

# 启用 UPX 压缩（减小体积）
python build.py --upx

# 自定义并行任务数（加速编译）
python build.py --jobs 4

# 查看所有选项
python build.py --help
```

编译完成后，可执行文件位于 `dist/release/` 目录。

---

## ⚡ 性能优化

### 🚀 GPU 加速支持

本项目的 AI 功能支持 GPU 加速，可大幅提升处理速度：

| 功能 | CPU 模式 | GPU 模式 | 提速倍数 |
|------|---------|---------|---------|
| AI 智能抠图 | ⚠️ 较慢 | ✅ 快速 | **3-10x** |
| AI 人声分离 | ⚠️ 较慢 | ✅ 快速 | **5-15x** |

### 🎯 平台特定说明

#### AI 功能（ONNX Runtime）

| 平台 | 默认版本 | GPU 支持 | 说明 |
|------|---------|---------|------|
| **Windows** | `onnxruntime-directml==1.22.0` | ✅ DirectML | 自动支持 Intel/AMD/NVIDIA GPU |
| **macOS (Apple Silicon)** | `onnxruntime==1.22.0` | ✅ CoreML | 内置硬件加速 |
| **macOS (Intel)** | `onnxruntime==1.22.0` | ⚠️ CPU | 无 GPU 加速 |
| **Linux** | `onnxruntime==1.22.0` | ⚠️ CPU | 可选 `onnxruntime-gpu` (CUDA) |

> 💡 **提示**：
> - **Windows 用户**：使用默认配置即可，自动支持 GPU 加速
> - **macOS 用户**：Apple Silicon 自动启用 CoreML 加速
> - **Linux 用户**：默认 CPU，如需 GPU 请安装 `onnxruntime-gpu`
> - 程序会自动检测并使用可用的 GPU，无需额外配置

#### 图片压缩工具

| 平台 | JPEG 压缩 | PNG 压缩 |
|------|----------|---------|
| **Windows** | ✅ mozjpeg + Pillow | ✅ pngquant + Pillow |
| **macOS** | ⚠️ Pillow | ✅ pngquant + Pillow |
| **Linux** | ⚠️ Pillow | ✅ pngquant + Pillow |

> 📝 mozjpeg 和 pngquant 会在首次使用时自动下载安装

#### 音视频处理（FFmpeg）

| 平台 | 支持 | 说明 |
|------|-----|------|
| **Windows** | ✅ | 使用 gyan.dev 提供的精简版 |
| **macOS** | ✅ | 使用 evermeet.cx 提供的官方版本 |
| **Linux** | ✅ | 使用 johnvansickle.com 静态编译版 |

> 📝 FFmpeg 会在首次使用时自动下载安装

---

## 🎨 界面特色

- ✨ **Material Design 3** - 遵循最新设计规范，界面精美流畅
- 🌙 **深色模式** - 自动跟随系统主题，保护视力
- 🎨 **毛玻璃效果** - 现代化的视觉体验
- 🎭 **自定义主题** - 支持多种主题颜色和字体选择
- 🔍 **全局搜索** - `Ctrl+K` 快速查找任何功能
- 📦 **批量处理** - 所有功能均支持批量操作

---

## 📝 常见问题

<details>
<summary><b>Q: 为什么推荐使用 uv 而不是 pip？</b></summary>

A: uv 是新一代 Python 包管理器，相比 pip 有以下优势：
- ⚡ **速度快** - 比 pip 快 10-100 倍
- 🔒 **可靠** - 锁定依赖版本，确保可重现构建
- 🎯 **简单** - 自动管理虚拟环境，一键安装所有依赖
- 🌍 **全局缓存** - 节省磁盘空间
</details>

<details>
<summary><b>Q: AI 功能需要联网吗？</b></summary>

A: 首次使用时需要联网下载模型文件（约 30-200 MB），下载后会缓存到本地，后续使用无需联网。
</details>

<details>
<summary><b>Q: 为什么没有 macOS 的 mozjpeg 支持？</b></summary>

A: mozjpeg 官方未提供 macOS 预编译版本。macOS 用户可以使用 Pillow 的 JPEG 压缩功能，质量也很不错。
</details>

<details>
<summary><b>Q: 如何切换主题？</b></summary>

A: 点击右上角的设置按钮 ⚙️，在"外观设置"中可以选择浅色/深色/自动模式，还可以自定义主题色和背景。
</details>

---

## 🤝 参与贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建新分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 开源协议

本项目采用 MIT 协议开源 - 详见 [LICENSE](./LICENSE) 文件

---

<div align="center">

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=HG-ha/MTools&type=Date)](https://star-history.com/#HG-ha/MTools&Date)

---

**Made with ❤️ using Python & Flet**

👨‍💻 **作者**：[HG-ha](https://github.com/HG-ha)

[GitHub](https://github.com/HG-ha) · [更多项目](https://github.com/HG-ha?tab=repositories) · [加入Q群 1029212047](https://qm.qq.com/q/vxxxgHGELu)

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

</div>
