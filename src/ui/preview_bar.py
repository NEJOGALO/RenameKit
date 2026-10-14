"""底部预览/统计栏：文件统计 + 撤销/执行按钮。"""

from __future__ import annotations

import customtkinter as ctk

from src.utils.i18n import T


class PreviewBar(ctk.CTkFrame):
    """底部固定操作栏（阶段 3 接统计、阶段 4 接撤销/执行）。"""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=52, corner_radius=0, **kwargs)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        self._on_execute = None   # 由主窗口注入
        self._total = 0
        self._conflicts = 0

        # 左：统计信息
        self.stats_label = ctk.CTkLabel(
            self,
            text=T["stats_zero"],
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        self.stats_label.grid(row=0, column=0, padx=16, pady=10, sticky="w")

        # 右：撤销 / 执行（阶段 4 启用）
        self.undo_btn = ctk.CTkButton(
            self,
            text=T["undo"],
            width=110,
            state="disabled",
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
        )
        self.undo_btn.grid(row=0, column=2, padx=(4, 6), pady=10)

        self.exec_btn = ctk.CTkButton(
            self,
            text=T["execute"],
            width=130,
            state="disabled",
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=self._on_execute,
        )
        self.exec_btn.grid(row=0, column=3, padx=(4, 16), pady=10)

    # ------------------------------------------------------------------
    def bind_actions(self, on_execute, on_undo) -> None:
        """注入执行/撤销回调（主窗口调用）。"""
        self._on_execute = on_execute
        self.undo_btn.configure(command=on_undo)
        self.exec_btn.configure(command=on_execute)

    def set_actions_enabled(self, execute: bool, undo: bool) -> None:
        """按状态切换两个按钮的可用性（含配色）。"""
        blue = ("#3B8ED0", "#1F6AA5")
        blue_hover = ("#36719F", "#144870")
        gray = ("gray75", "gray30")
        gray_hover = ("gray65", "gray40")

        if execute:
            self.exec_btn.configure(state="normal", fg_color=blue, hover_color=blue_hover)
        else:
            self.exec_btn.configure(state="disabled", fg_color=gray, hover_color=gray_hover)
        if undo:
            self.undo_btn.configure(state="normal", fg_color=blue, hover_color=blue_hover)
        else:
            self.undo_btn.configure(state="disabled", fg_color=gray, hover_color=gray_hover)

    def set_progress(self, text: str | None) -> None:
        """执行中把进度写进统计栏（text=None 恢复常规统计）。"""
        if text is None:
            self.set_stats(self._total, self._conflicts)
        else:
            self.stats_label.configure(text=text)

    def set_stats(self, total: int, conflicts: int = 0) -> None:
        """更新底部统计文案。"""
        self._total = total
        self._conflicts = conflicts
        if conflicts:
            self.stats_label.configure(text=f"共 {total} 个文件，{conflicts} 个冲突")
        else:
            self.stats_label.configure(text=f"共 {total} 个文件")
