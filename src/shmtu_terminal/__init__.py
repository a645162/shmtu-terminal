"""上海海事大学校园终端聚合包。

聚合仓库内各子模块 (CAS / OCR / 同步等) 暴露的能力,提供统一的 Python SDK
与 CLI 入口。
"""

from __future__ import annotations

from shmtu_terminal.core import greet

__version__ = "0.1.0"
__all__ = ["__version__", "greet"]
