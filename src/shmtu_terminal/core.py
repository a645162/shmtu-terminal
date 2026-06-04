"""核心工具函数与运行时配置。"""

from __future__ import annotations

PACKAGE_NAME = "shmtu-terminal"


def greet(name: str) -> str:
    """返回对 `name` 的问候字符串。

    Args:
        name: 被问候的对象名称。

    Returns:
        标准问候字符串。
    """
    return f"Hello, {name}!"
