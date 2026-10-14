# -*- mode: python ; coding: utf-8 -*-
"""RenameKit PyInstaller 打包配置（单文件 exe，Windows x64 专用裁剪版）。

关键点：
- collect_all('tkinterdnd2'/'customtkinter') 收集全部资源，
  随后按平台裁剪 tkdnd：只留 win-x64 / win-x64-tcl9（Python 3.14
  带 Tcl 9，运行时用 -tcl9 目录），剔除 linux/osx/其他架构，
  体积从 ~21.5MB 压到 <15MB；
- assets/icon.ico 作为 exe 文件图标；
- assets/logo.png 以 datas 放入 assets/，与 widgets.load_logo_image
  的解析路径一致。
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent  # build/ 的上一级 = 项目根目录

datas, binaries, hiddenimports = [], [], []
for pkg in ("tkinterdnd2", "customtkinter"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h


def _is_tkdnd(path: str) -> bool:
    return "tkdnd" in path.replace("\\", "/").lower()


def _keep_win64(items: list) -> list:
    """tkdnd 只保留 Windows x64（含 tcl9 变体），其余平台剔除。"""
    kept = []
    for item in items:
        src = str(item[0]).replace("\\", "/")
        if _is_tkdnd(src) and not any(
            seg in src for seg in ("tkdnd/win-x64/", "tkdnd/win-x64-tcl9/")
        ):
            continue
        kept.append(item)
    return kept


datas = _keep_win64(datas)
binaries = _keep_win64(binaries)

# Pillow 剔除用不到的编解码 pyd（惰性插件，缺失时 Image.init 自动跳过，
# png/jpg 不受影响；本工具只加载 logo.png）——省 ~8MB 未压缩
_PIL_DROP = ("_avif", "_webp", "_imagingcms")
binaries = [
    b for b in binaries
    if not ("PIL" in str(b[0]).replace("\\", "/") and any(d in str(b[0]) for d in _PIL_DROP))
]

datas.append((str(ROOT / "assets" / "logo.png"), "assets"))
datas.append((str(ROOT / "assets" / "icon.ico"), "assets"))

a = Analysis(
    [str(ROOT / "src" / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 精简：
    # - ssl/_ssl：纯本地工具无网络调用（已实测运行路径不加载 ssl/urllib.request）
    # - unittest/pydoc/doctest/difflib/tkinter.test：明显用不到
    excludes=[
        "ssl", "_ssl",
        "unittest", "pydoc", "doctest", "difflib", "tkinter.test",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# Analysis 内部依赖解析产生的二进制精简（已实测运行路径不加载这些）：
# - PIL 的 avif/webp/cms 编解码 pyd：惰性插件，缺失只影响对应格式，png 正常
# - OpenSSL 组 + _hashlib：纯本地工具无网络/哈希调用
#   （实测 ssl/_ssl/urllib.request/hashlib 运行时均未进 sys.modules）
_DROP = ("_avif", "_webp", "_imagingcms", "libcrypto-3", "libssl-3",
         "_ssl.", "_hashlib")
a.binaries = [
    b for b in a.binaries
    if not any(d in str(b[0]) for d in _DROP)
]

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RenameKit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # 窗口程序，不弹控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icon.ico"),
)
