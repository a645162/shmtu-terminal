"""命令行入口 (基于 Typer)。"""

from __future__ import annotations

import typer

from shmtu_terminal import __version__, greet

app = typer.Typer(
    name="shmtu-terminal",
    help="上海海事大学校园终端聚合 CLI。",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """打印当前版本号。"""
    typer.echo(__version__)


@app.command()
def hello(name: str = typer.Argument(..., help="问候对象名称")) -> None:
    """输出一条问候。"""
    typer.echo(greet(name))


if __name__ == "__main__":
    app()
