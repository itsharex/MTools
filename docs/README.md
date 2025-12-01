# MTools 文档中心

欢迎访问 MTools 项目文档！

## 📖 文档列表

### [编译指南](./build_guide.md)
完整的项目编译指南，包括：
- 环境配置
- 编译命令详解
- 常见问题解答
- 优化建议

## 🔗 快速链接

### 编译相关

- **快速开始编译**
  ```bash
  python build.py
  ```

- **开发模式编译**
  ```bash
  python build.py --mode dev
  ```

- **查看帮助**
  ```bash
  python build.py --help
  ```

### 常用命令

| 命令 | 说明 |
|------|------|
| `uv sync` | 同步项目依赖 |
| `python src/main.py` | 直接运行（不编译） |
| `python build.py` | Release 编译 |
| `python build.py --mode dev` | Dev 编译 |
| `python build.py --upx --jobs 4` | UPX 压缩 + 4 核编译 |

## 📚 更多资源

- [项目主 README](../README.md)
- [Nuitka 官方文档](https://nuitka.net/)
- [UPX 下载](https://github.com/upx/upx/releases)

---

如有问题，欢迎提交 Issue！

