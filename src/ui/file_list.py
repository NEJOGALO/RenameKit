"""文件列表组件：两列 Treeview（原文件名 → 新文件名）+ 拖拽导入 + 空态占位。"""

from __future__ import annotations

import customtkinter as ctk
from tkinter import ttk, filedialog

from src.core.models import FileItem
from src.ui.widgets import apply_treeview_style
from src.utils.i18n import T


class FileList(ctk.CTkFrame):
    """右侧文件列表区：树形列表、滚动条、空态提示、底部操作按钮。"""

    def __init__(self, master, on_paths_dropped=None, on_add_files=None,
                 on_add_folder=None, on_clear=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_paths_dropped = on_paths_dropped
        self._on_add_files_cb = on_add_files
        self._on_add_folder_cb = on_add_folder
        self._on_clear_cb = on_clear

        apply_treeview_style(dark=True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 两列列表，列宽 1:1 且都允许拉伸
        self.tree = ttk.Treeview(
            self,
            columns=("original", "new"),
            show="headings",
            selectmode="extended",
        )
        self.tree.heading("original", text=T["col_original"], anchor="w")
        self.tree.heading("new", text=T["col_new"], anchor="w")
        self.tree.column("original", width=380, minwidth=120, stretch=True, anchor="w")
        self.tree.column("new", width=380, minwidth=120, stretch=True, anchor="w")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # 状态行配色（随主题切换更新）
        self.apply_status_tags(ctk.get_appearance_mode().lower() == "dark")

        # 窗口缩放时保持两列宽度约 1:1
        self.tree.bind("<Configure>", self._on_resize, add="+")

        # 空态占位文案（叠加在列表中央，有文件后由 set_files 隐藏）
        self.empty_label = ctk.CTkLabel(
            self,
            text=T["empty_files"],
            text_color=("gray40", "gray60"),
            font=ctk.CTkFont(size=13),
            justify="center",
        )
        self.empty_label.place(relx=0.5, rely=0.45, anchor="center")

        # 底部按钮行 + 子目录选项
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(6, 8))
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(btn_row, text=T["add_files"], width=110,
                      command=self._add_files_clicked).grid(row=0, column=0, padx=4)
        ctk.CTkButton(btn_row, text=T["add_folder"], width=110,
                      command=self._add_folder_clicked).grid(row=0, column=1, padx=4)
        ctk.CTkButton(
            btn_row, text=T["clear_list"], width=110,
            fg_color=("gray75", "gray30"), hover_color=("gray65", "gray40"),
            command=self._clear_clicked,
        ).grid(row=0, column=2, padx=4)

        self.include_subdirs = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            btn_row, text=T["include_subdirs"], variable=self.include_subdirs,
            height=26, checkbox_width=16, checkbox_height=16,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=3, padx=(10, 4))

        # 拖拽注册（self 覆盖整个区域；tree 覆盖其上方的列表部分。
        # 重复触发无害：导入按路径去重。）
        self._enable_dnd()

    # ------------------------------------------------------------------
    def _enable_dnd(self) -> None:
        """注册为拖拽投放目标；扩展加载失败时静默降级为按钮导入。"""
        try:
            from tkinterdnd2 import DND_FILES

            for widget in (self, self.tree):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_drop, add="+")
        except Exception:
            pass  # 拖拽不可用时按钮导入仍可用

    def _on_drop(self, event):
        """处理文件拖拽投放。必须返回动作类型（copy = 保留源文件）。"""
        from tkinterdnd2 import COPY

        if self.on_paths_dropped:
            try:
                paths = list(self.tk.splitlist(event.data))
            except Exception:
                paths = [event.data]
            if paths:
                self.on_paths_dropped(paths)
        return COPY

    # ------------------------------------------------------------------
    def _on_resize(self, event) -> None:
        """保持两列宽度约 1:1。"""
        total = event.width
        if total <= 1:
            return
        half = total // 2
        self.tree.column("original", width=half)
        self.tree.column("new", width=total - half)

    def _add_files_clicked(self) -> None:
        if self._on_add_files_cb:
            self._on_add_files_cb()
            return
        filedialog.askopenfilenames(title=T["select_files"])

    def _add_folder_clicked(self) -> None:
        if self._on_add_folder_cb:
            self._on_add_folder_cb()
            return
        folder = filedialog.askdirectory(title=T["select_folder"])
        if folder and self.on_paths_dropped:
            self.on_paths_dropped([folder])

    def _clear_clicked(self) -> None:
        if self._on_clear_cb:
            self._on_clear_cb()
            return
        self.set_files([])

    # ------------------------------------------------------------------
    def apply_status_tags(self, dark: bool) -> None:
        """按主题配置状态行配色：批内冲突黄、外部冲突/非法红、未变灰。"""
        yellow = "#f1c40f" if dark else "#b7950b"
        red = "#e74c3c" if dark else "#c0392b"
        gray = "#7a7a7a" if dark else "#999999"
        self.tree.tag_configure("conflict", foreground=yellow)
        self.tree.tag_configure("disk_conflict", foreground=red)
        self.tree.tag_configure("invalid", foreground=red)
        self.tree.tag_configure("unchanged", foreground=gray)

    def set_files(self, items: list[FileItem]) -> None:
        """按 FileItem 列表刷新显示（含状态标红），空列表时显示占位文案。"""
        self.tree.delete(*self.tree.get_children())
        if items:
            self.empty_label.place_forget()
            for item in items:
                self.tree.insert(
                    "", "end",
                    values=(item.original_name, item.new_name),
                    tags=(item.status,),
                )
        else:
            self.empty_label.place(relx=0.5, rely=0.45, anchor="center")
