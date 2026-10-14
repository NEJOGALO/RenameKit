"""自定义通用控件与样式工具。"""

from __future__ import annotations

import customtkinter as ctk
from tkinter import ttk


def apply_treeview_style(dark: bool) -> None:
    """手动适配 ttk.Treeview 配色，使其跟随 CustomTkinter 主题。

    ttk 控件不走 CTk 的主题系统，切换深浅色后必须手动改样式，
    否则列表区会保持旧配色、出现“黑白拼接”。
    """
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except ttk.TclError:
        pass

    if dark:
        style.configure(
            "Treeview",
            background="#2b2b2b",
            fieldbackground="#2b2b2b",
            foreground="#e0e0e0",
            rowheight=28,
            borderwidth=0,
            relief="flat",
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#343638",
            foreground="#e0e0e0",
            relief="flat",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", "#1f538d")],
            foreground=[("selected", "#ffffff")],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#3d4042")],
        )
    else:
        style.configure(
            "Treeview",
            background="#f5f5f5",
            fieldbackground="#f5f5f5",
            foreground="#222222",
            rowheight=28,
            borderwidth=0,
            relief="flat",
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#e0e0e0",
            foreground="#222222",
            relief="flat",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", "#1f538d")],
            foreground=[("selected", "#ffffff")],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#d0d0d0")],
        )


def center_window(win: ctk.CTk, width: int, height: int) -> None:
    """把窗口居中显示在当前屏幕上。"""
    win.update_idletasks()
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    win.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")


def load_logo_image(size: int = 26) -> ctk.CTkImage | None:
    """加载 assets/logo.png 占位图；文件缺失或加载失败时返回 None。"""
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "assets" / "logo.png"
    if not path.exists():
        return None
    try:
        from PIL import Image

        img = Image.open(path)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        return None
