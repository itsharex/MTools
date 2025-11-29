# 工具目录说明

本目录包含图片和视频处理所需的第三方工具。

## FFmpeg（已包含）

用于视频和音频处理的完整工具。

- **位置**: `windows/ffmpeg/bin/`
- **已包含**: 是
- **用途**: 视频压缩、格式转换、音频提取等

## 图片压缩工具（自动安装）

以下图片压缩工具支持自动下载安装：

### mozjpeg

高效的 JPEG 压缩工具，由 Mozilla 开发维护。

- **自动安装**: 是
- **手动下载**: https://ghproxy.cn/https://github.com/mozilla/mozjpeg/releases/download/v4.0.3/mozjpeg-v4.0.3-win-x64.zip
- **安装位置**:
  - Windows: `bin/windows/mozjpeg/shared/Release/cjpeg.exe`
  - macOS: `bin/macos/mozjpeg/cjpeg`
  - Linux: `bin/linux/mozjpeg/cjpeg`
- **大小**: 约 5 MB
- **功能**: 可减小 JPEG 文件 50-70% 的大小
- **许可证**: BSD-3-Clause

### pngquant

高质量的 PNG 压缩工具，支持有损压缩。

- **自动安装**: 是
- **手动下载**: https://pngquant.org/pngquant-windows.zip
- **安装位置**:
  - Windows: `bin/windows/pngquant/pngquant/pngquant.exe`
  - macOS: `bin/macos/pngquant/pngquant`
  - Linux: `bin/linux/pngquant/pngquant`
- **大小**: 约 300 KB
- **功能**: 可减小 PNG 文件 60-80% 的大小
- **许可证**: GPL v3 / Commercial

## 自动安装说明

### Windows 平台（推荐）

当您在软件中选择"标准模式"进行图片压缩时，如果检测到工具未安装，软件会：

1. 自动显示安装页面
2. 点击"开始安装"按钮
3. 软件会自动下载 mozjpeg 和 pngquant
4. 自动解压并安装到正确的位置
5. 安装完成后即可使用

整个过程无需手动操作，完全自动化！

### macOS 和 Linux 平台

由于这些平台的工具需要编译或通过包管理器安装，建议：

#### macOS
```bash
# 使用 Homebrew 安装
brew install mozjpeg
brew install pngquant
```

#### Linux (Ubuntu/Debian)
```bash
# 安装 pngquant
sudo apt install pngquant

# mozjpeg 需要从源码编译或下载预编译版本
```

## 注意事项

1. **自动安装仅支持 Windows 平台**
2. 如果您只使用"快速模式"或"极限模式"压缩，无需安装 mozjpeg 和 pngquant
3. FFmpeg 已经包含在软件中，无需额外下载
4. 自动安装需要网络连接，下载速度取决于您的网络环境
5. 工具会被安装到应用程序的 bin 目录，不会影响系统环境

## 手动安装（可选）

如果自动安装失败，您可以手动下载并安装：

1. 从上述地址下载对应的压缩包
2. 解压到对应的目录结构中：
   - mozjpeg: 解压所有内容到 `bin/windows/mozjpeg/`
   - pngquant: 解压后确保 `pngquant.exe` 位于 `bin/windows/pngquant/pngquant/`
3. 重新运行软件，工具将自动被识别

## 目录结构

```
bin/
├── windows/
│   ├── ffmpeg/          # FFmpeg（已包含）
│   │   └── bin/
│   │       ├── ffmpeg.exe
│   │       ├── ffprobe.exe
│   │       └── ffplay.exe
│   ├── mozjpeg/         # mozjpeg（自动安装）
│   │   ├── shared/
│   │   │   └── Release/
│   │   │       └── cjpeg.exe
│   │   └── static/
│   └── pngquant/        # pngquant（自动安装）
│       └── pngquant/
│           └── pngquant.exe
├── macos/               # macOS 平台工具目录
└── linux/               # Linux 平台工具目录
```

