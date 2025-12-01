# MTools 编译指南

本指南将帮助您使用 Nuitka 编译 MTools 项目，生成独立的可执行文件。

## 📋 前置要求

### 必需环境

1. **Python 3.11**
   ```bash
   python --version  # 应显示 3.11.x
   ```

2. **uv 包管理器** (推荐)
   ```bash
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # 或使用 pip
   pip install uv
   ```

3. **C 编译器**
   - **Windows**: 安装 Visual Studio Build Tools 或完整的 Visual Studio
     - [下载地址](https://visualstudio.microsoft.com/downloads/)
     - 选择 "Desktop development with C++" 工作负载
   - **Linux**: GCC (`sudo apt install build-essential`)
   - **macOS**: Xcode Command Line Tools (`xcode-select --install`)

### 可选工具

4. **UPX** (用于压缩可执行文件，可选)
   - [下载地址](https://github.com/upx/upx/releases)
   - Windows: 下载后解压到任意目录，并添加到系统 PATH 环境变量

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
cd H:\Workspace\PythonProjects\mytools

# 同步依赖（包括 Nuitka）
uv sync
```

### 2. 基础编译

**Release 模式（生产环境）**
```bash
python build.py
```
- ✅ 完整优化
- ✅ 无控制台窗口
- ✅ 体积较小，性能最佳
- ⏱️ 编译时间较长 (10-30分钟)

**Dev 模式（开发测试）**
```bash
python build.py --mode dev
```
- ✅ 快速编译
- ✅ 保留控制台窗口（可查看日志）
- ✅ 保留调试信息
- ⏱️ 编译时间较短 (5-15分钟)

### 3. 高级选项

**启用 UPX 压缩**
```bash
python build.py --upx
```
- 自动检测系统 PATH 中的 UPX
- 进一步减小文件体积（约 30-50%）

**指定 UPX 路径**
```bash
python build.py --upx --upx-path "C:\tools\upx\upx.exe"
```

**调整并行任务数**
```bash
# 使用 4 个并行任务（编译更快，但占用更多资源）
python build.py --jobs 4

# 使用 1 个任务（最安全，系统配置低时推荐）
python build.py --jobs 1
```

**组合使用**
```bash
# 完整优化 + UPX + 4 核并行
python build.py --mode release --upx --jobs 4

# 快速测试编译
python build.py --mode dev --jobs 1
```

## 📊 构建模式对比

| 特性 | Dev 模式 | Release 模式 |
|------|---------|-------------|
| **编译速度** | 快 ⚡ (5-15分钟) | 慢 🐢 (10-30分钟) |
| **控制台窗口** | 显示 👁️ | 隐藏 🙈 |
| **优化级别** | 低 (保留调试) | 高 (完整优化) |
| **文件体积** | 较大 | 较小 |
| **启动速度** | 较慢 | 较快 |
| **适用场景** | 开发测试 | 正式发布 |
| **Python 标志** | `no_site` | `-O`, `no_site`, `no_warnings` |

## ⚙️ 命令行参数详解

查看所有可用参数：
```bash
python build.py --help
```

### `--mode {release,dev}`
- **默认**: `release`
- **说明**: 构建模式
  - `release`: 生产环境，完整优化
  - `dev`: 开发环境，快速编译

### `--upx`
- **默认**: 不启用
- **说明**: 启用 UPX 压缩
- **前提**: 需要安装 UPX 工具

### `--upx-path PATH`
- **默认**: 无
- **说明**: 指定 UPX 可执行文件的完整路径
- **示例**: `--upx-path "C:\upx\upx.exe"`

### `--jobs N`
- **默认**: `2`
- **说明**: 并行编译任务数
- **建议**: 
  - 低配置电脑: `1`
  - 中等配置: `2-4`
  - 高配置: `4-8` (不要超过 CPU 核心数)

## 🗂️ 输出结构

编译完成后，文件位于 `dist/release/` 目录：

```
dist/release/
├── MTools_x64/           # 可执行程序目录
│   ├── MTools.exe        # 主程序
│   ├── src/assets/       # 资源文件
│   └── *.dll             # 依赖库
└── MTools_Windows_AMD64.zip  # 压缩包（自动生成）
```

## 💡 优化建议

### 减小文件体积

1. **启用 UPX 压缩**
   ```bash
   python build.py --upx
   ```
   - 可减小 30-50% 体积
   - 略微增加启动时间（几毫秒）

2. **检查依赖**
   - 移除不必要的依赖包
   - 使用轻量级替代方案

### 加快编译速度

1. **增加并行任务数**
   ```bash
   python build.py --jobs 4
   ```
   - 充分利用多核 CPU
   - 注意内存占用

2. **使用 Dev 模式测试**
   ```bash
   python build.py --mode dev --jobs 4
   ```
   - 快速验证功能
   - 确认无误后再用 Release 编译

### 避免系统卡顿

1. **降低并行度**
   ```bash
   python build.py --jobs 1
   ```

2. **关闭其他程序**
   - 编译时关闭浏览器、IDE 等
   - 确保有足够的磁盘空间（至少 5GB）

3. **不要操作电脑**
   - 让编译过程在后台安静进行
   - 可能需要 10-30 分钟

## 🐛 常见问题

### Q1: 提示 "No module named nuitka"

**解决方案**:
```bash
uv sync  # 重新同步依赖
```

### Q2: 编译过程中电脑卡死

**原因**: 并行任务数过高，资源占用过大

**解决方案**:
```bash
python build.py --jobs 1  # 降低并行度
```

### Q3: UPX 压缩失败

**检查 UPX 安装**:
```bash
# 检查 UPX 是否在 PATH 中
upx --version

# 如果不在 PATH，指定完整路径
python build.py --upx --upx-path "C:\path\to\upx.exe"
```

### Q4: 找不到 C 编译器

**Windows 解决方案**:
1. 安装 [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/)
2. 勾选 "Desktop development with C++"
3. 重启终端

**Linux 解决方案**:
```bash
sudo apt install build-essential
```

### Q5: 编译成功但程序无法运行

**检查项**:
1. 确保 `src/assets/` 目录存在且包含必要文件
2. 检查 `dist/release/MTools_x64/src/assets/` 是否正确复制
3. 使用 Dev 模式查看错误信息:
   ```bash
   python build.py --mode dev
   ```

### Q6: 编译时间过长

**正常情况**:
- Dev 模式: 5-15 分钟
- Release 模式: 10-30 分钟

**如果超过 1 小时**:
1. 检查磁盘空间是否充足
2. 检查是否卡在某个步骤（查看输出日志）
3. 尝试 `Ctrl+C` 中断，重新编译

## 📚 进阶主题

### 自定义编译选项

如需更多自定义选项，可直接修改 `build.py` 中的 `get_nuitka_cmd()` 函数。

Nuitka 官方文档: https://nuitka.net/doc/user-manual.html

### 跨平台编译

当前 `build.py` 支持：
- ✅ Windows
- ✅ Linux
- ✅ macOS (需要 .icns 图标)

在对应平台上运行 `python build.py` 即可。

### CI/CD 集成

```yaml
# GitHub Actions 示例
- name: Build with Nuitka
  run: |
    uv sync
    python build.py --mode release --jobs 2
```

## 📞 获取帮助

- **项目 Issue**: 提交到项目 GitHub Issues
- **Nuitka 文档**: https://nuitka.net/
- **UPX 文档**: https://upx.github.io/

---

**最后更新**: 2025-12-01

