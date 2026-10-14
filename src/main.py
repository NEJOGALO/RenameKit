"""RenameKit 程序入口。

启动命令（在 D:\RenameKit 目录下）：
    .venv\\Scripts\\python src\\main.py
或：
    .venv\\Scripts\\python -m src.main
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_path() -> None:
    """直接以脚本方式运行时，把项目根目录加入 sys.path。"""
    if not __package__:
        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))


_ensure_path()

from src.ui.app import RenameKitApp  # noqa: E402
from src.utils import config as config_store  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402


def main() -> None:
    """初始化日志与配置，启动主窗口。"""
    setup_logger()
    cfg = config_store.load_config()
    app = RenameKitApp(cfg)
    app.mainloop()


if __name__ == "__main__":
    main()
