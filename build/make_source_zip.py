"""打包源码运行版 zip：dist/RenameKit-source.zip。

内容（zip 根即解压根，解压到空目录直接可用）：
    src/  assets/  build/renamkit.spec
    requirements.txt  启动.bat  README.md  LICENSE

排除：.venv、dist、build/work、__pycache__、各类临时产物。
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "RenameKit-source.zip"

# (源路径, zip 内前缀)；None 前缀 = 直接放根
INCLUDE: list[tuple[Path, str | None]] = [
    (ROOT / "src", "src"),
    (ROOT / "assets", "assets"),
    (ROOT / "docs", "docs"),
    (ROOT / "build" / "renamkit.spec", "build/renamkit.spec"),
    (ROOT / "requirements.txt", None),
    (ROOT / "启动.bat", None),
    (ROOT / "README.md", None),
    (ROOT / "LICENSE", None),
]

EXCLUDE_DIRS = {"__pycache__", ".venv", "work"}
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".zip"}


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src, prefix in INCLUDE:
            if not src.exists():
                print(f"跳过（不存在）: {src}")
                continue
            if src.is_file():
                zf.write(src, prefix or src.name)
                count += 1
                continue
            for p in sorted(src.rglob("*")):
                if not p.is_file():
                    continue
                if p.suffix in EXCLUDE_SUFFIX:
                    continue
                if EXCLUDE_DIRS & set(p.relative_to(src).parts):
                    continue
                arc = f"{prefix}/{p.relative_to(src).as_posix()}" if prefix else p.name
                zf.write(p, arc)
                count += 1
    print(f"{OUT.name}: {count} 个文件, {OUT.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
