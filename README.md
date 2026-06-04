# shmtu-terminal

上海海事大学校园终端聚合包，提供 CLI 入口与 Python SDK，聚合仓库内各子模块
（CAS / OCR / 同步等）能力。

## Clone

```bash
git clone --recurse-submodules https://github.com/a645162/shmtu-terminal
```

```bash
git submodule update --init --recursive
```

## 安装

仓库根目录本身就是可独立构建/安装的 Python 项目（`src/` 布局）：

```bash
# 基础安装（CLI 入口 shmtu-terminal）
pip install -e .

# 本地可编辑安装 CAS 子模块
pip install -e ./Lib/shmtu-cas-python
```

## CLI

```bash
shmtu-terminal --help
shmtu-terminal hello 上海海事大学
shmtu-terminal version
```

## Python API

```python
from shmtu_terminal import __version__, greet

print(__version__)         # '0.1.0'
print(greet("SHMTU"))      # 'Hello, SHMTU!'
```

## 子模块

本仓库聚合若干 git submodule，按需启用：

| 子模块 | 路径 | 说明 |
| --- | --- | --- |
| shmtu-cas-python | `Lib/shmtu-cas-python` | 上海海事大学 CAS Python 客户端 |
| shmtu-cas-ocr-model | `Model/shmtu-cas-ocr-model` | CAS 验证码 OCR 模型 |
| shmtu-cas-ocr-server | `Server/shmtu-cas-ocr-server` | C++ OCR 服务 |
| smu-badminton | `Server/smu-badminton` | 羽毛球场预约系统 |
| shmtu-server-unofficial | `Server/shmtu-server-unofficial` | Spring Boot 后端服务 |
| shmtu-cas-ocr-crx | `Plugin/shmtu-cas-ocr-crx` | 浏览器扩展 (Chrome Extension)，CAS 验证码 OCR 自动识别 |

子模块各自维护 `pyproject.toml` / `build.gradle` / `Cargo.toml`，与本聚合包独立。
