"""主窗口：标题栏、左侧可折叠规则面板、右侧文件列表、底部操作栏。"""

from __future__ import annotations

import os
from tkinter import messagebox, filedialog

import customtkinter as ctk

from src.core.models import FileItem, OperationRecord, RenameRule
from src.core.renamer import execute_operations
from src.core.rules import RuleEngine
from src.core import undo as undo_stack
from src.core.validator import validate
from src.ui.file_list import FileList
from src.ui.preview_bar import PreviewBar
from src.ui.rule_panel import RulePanel
from src.ui.widgets import apply_treeview_style, center_window, load_logo_image
from src.utils import config as config_store
from src.utils.i18n import T
from src.utils.logger import get_logger

logger = get_logger()


class RenameKitApp(ctk.CTk):
    """RenameKit 主窗口。"""

    DEFAULT_W = 1100
    DEFAULT_H = 700
    MIN_W = 900
    MIN_H = 600
    PANEL_W = 280   # 规则面板展开宽度
    STRIP_W = 48    # 折叠后仅保留箭头条宽度

    def __init__(self, cfg: dict | None = None):
        super().__init__()
        self.cfg = cfg if cfg is not None else config_store.load_config()
        self._panel_expanded = True

        # 状态：文件列表与规则链
        self.files: list[FileItem] = []
        self.rules: list[RenameRule] = []

        self.title(T["app_title"])
        self.minsize(self.MIN_W, self.MIN_H)
        self._set_window_icon()

        # 主题：按配置启动，并同步 Treeview 配色
        theme = self.cfg.get("theme", "dark")
        if theme not in ("dark", "light"):
            theme = "dark"
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")
        apply_treeview_style(dark=(theme == "dark"))

        self._enable_dnd()
        self._build_layout()
        center_window(self, self.DEFAULT_W, self.DEFAULT_H)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # 拖拽
    # ------------------------------------------------------------------
    def _set_window_icon(self) -> None:
        """设置窗口图标（源码与打包环境路径不同，失败静默）。"""
        try:
            from pathlib import Path

            ico = Path(__file__).resolve().parents[2] / "assets" / "icon.ico"
            if ico.exists():
                self.iconbitmap(str(ico))
        except Exception:
            pass

    def _enable_dnd(self) -> None:
        """把 tkdnd 扩展挂到本窗口（CustomTkinter 官方集成入口）。"""
        try:
            from tkinterdnd2 import TkinterDnD

            version = TkinterDnD.require(self)
            logger.info("tkdnd 扩展加载成功 version=%s", version)
        except Exception:
            logger.exception("tkdnd 加载失败，拖拽导入不可用（按钮导入仍可用）")

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        """构建三区布局：标题栏 / 主体 / 底部操作栏。"""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_title_bar()

        # --- 左侧：可折叠规则面板 ---
        self.left_container = ctk.CTkFrame(self, width=self.PANEL_W, corner_radius=0)
        self.left_container.grid(row=1, column=0, sticky="nsew")
        self.left_container.grid_propagate(False)  # 固定宽度，折叠时不被内容撑开
        self.left_container.grid_rowconfigure(1, weight=1)
        self.left_container.grid_columnconfigure(0, weight=1)

        # 折叠/展开按钮（位于面板顶部）
        self.collapse_btn = ctk.CTkButton(
            self.left_container,
            text="◀",
            width=36,
            height=30,
            corner_radius=6,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=self._toggle_panel,
        )
        self.collapse_btn.grid(row=0, column=0, padx=6, pady=(8, 4), sticky="w")

        # 面板内容
        self.rule_panel = RulePanel(
            self.left_container, self.rules, on_change=self._recompute,
        )
        self.rule_panel.grid(row=1, column=0, sticky="nsew", pady=(2, 8))

        # --- 右侧：文件列表 ---
        self.file_list = FileList(
            self,
            corner_radius=0,
            on_paths_dropped=self._import_paths,
            on_add_files=self._pick_files,
            on_add_folder=self._pick_folder,
            on_clear=self._clear_files,
        )
        self.file_list.grid(row=1, column=1, sticky="nsew", padx=(0, 8), pady=(8, 0))

        # --- 底部：统计与操作 ---
        self.preview_bar = PreviewBar(self)
        self.preview_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.preview_bar.bind_actions(self._on_execute, self._on_undo)

        # 启动维护：清理探测残留 + 悬挂记录提示
        self.after(200, self._startup_maintenance)

    def _build_title_bar(self) -> None:
        """顶部标题栏：Logo + 标题（左），主题/关于/GitHub（右）。"""
        bar = ctk.CTkFrame(self, height=52, corner_radius=0)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)

        # Logo 占位图
        logo = load_logo_image(size=26)
        if logo is not None:
            ctk.CTkLabel(bar, image=logo, text="").grid(
                row=0, column=0, padx=(14, 6), pady=10
            )
        else:
            ctk.CTkLabel(
                bar, text="R", font=ctk.CTkFont(size=18, weight="bold")
            ).grid(row=0, column=0, padx=(14, 6), pady=10)

        # 标题
        ctk.CTkLabel(
            bar,
            text=T["app_title"],
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        # 右侧按钮：主题切换 → 关于 → GitHub
        self.theme_btn = ctk.CTkButton(
            bar, width=96, text=self._theme_btn_text(),
            command=self._toggle_theme,
        )
        self.theme_btn.grid(row=0, column=2, padx=4, pady=10)

        ctk.CTkButton(
            bar, width=80, text=T["about"],
            fg_color=("gray60", "gray25"),
            hover_color=("gray50", "gray35"),
            command=lambda: messagebox.showinfo(T["app_title"], T["about_text"]),
        ).grid(row=0, column=3, padx=4, pady=10)

        ctk.CTkButton(
            bar, width=90, text=T["github"],
            fg_color=("gray60", "gray25"),
            hover_color=("gray50", "gray35"),
            command=lambda: messagebox.showinfo(T["app_title"], T["github_text"]),
        ).grid(row=0, column=4, padx=(4, 14), pady=10)

    # ------------------------------------------------------------------
    # 文件导入
    # ------------------------------------------------------------------
    def _pick_files(self) -> None:
        """「添加文件」按钮：文件多选对话框。"""
        paths = filedialog.askopenfilenames(title=T["select_files"], parent=self)
        if paths:
            self._import_paths(list(paths))

    def _pick_folder(self) -> None:
        """「添加文件夹」按钮：目录选择对话框。"""
        folder = filedialog.askdirectory(title=T["select_folder"], parent=self)
        if folder:
            self._import_paths([folder])

    def _clear_files(self) -> None:
        """清空文件列表。"""
        self.files.clear()
        self._recompute()

    def _import_paths(self, paths: list[str]) -> None:
        """导入文件/文件夹路径：展开目录、过滤、去重、排序、刷新。"""
        include_sub = bool(self.file_list.include_subdirs.get())
        collected: list[str] = []

        for raw in paths:
            path = os.path.normpath(raw.strip().strip('"'))
            if os.path.isdir(path):
                if include_sub:
                    for root, _dirs, names in os.walk(path):
                        for name in names:
                            collected.append(os.path.join(root, name))
                else:
                    for name in os.listdir(path):
                        full = os.path.join(path, name)
                        if os.path.isfile(full):
                            collected.append(full)
            elif os.path.isfile(path):
                collected.append(path)

        if not collected:
            return

        # 已有 + 新增，按规范化路径去重
        known = {os.path.normcase(f.original_path) for f in self.files}
        added = 0
        for path in collected:
            key = os.path.normcase(path)
            if key in known:
                continue
            known.add(key)
            self.files.append(
                FileItem(original_path=path, original_name=os.path.basename(path))
            )
            added += 1

        if added:
            # 按文件名排序
            self.files.sort(key=lambda f: f.original_name.lower())
            logger.info("导入 %d 个文件（跳过重复 %d 个）", added,
                        len(collected) - added)
        self._recompute()

    # ------------------------------------------------------------------
    # 规则重算
    # ------------------------------------------------------------------
    def _recompute(self) -> None:
        """用当前规则链重算所有文件的新文件名，校验后刷新列表与统计。"""
        engine = RuleEngine(self.rules)
        total = len(self.files)
        for i, item in enumerate(self.files):
            item.new_name = engine.apply(item.original_name, i, total)
        issues = validate(self.files)
        self.file_list.set_files(self.files)
        self.preview_bar.set_stats(total, issues)
        # 按钮联动：无冲突且有实际变更才可执行；撤销取决于 undo 栈
        has_changes = any(f.new_name != f.original_name for f in self.files)
        self.preview_bar.set_actions_enabled(
            execute=(has_changes and issues == 0),
            undo=undo_stack.has_undoable(),
        )

    # ------------------------------------------------------------------
    # 执行 / 撤销（阶段 4）
    # ------------------------------------------------------------------
    def _set_busy(self, busy: bool) -> None:
        """执行期间的视觉反馈：等待光标 + 禁用操作按钮。"""
        self.configure(cursor="wait" if busy else "")
        if busy:
            self.preview_bar.set_actions_enabled(False, False)
        self.update_idletasks()

    def _progress_cb(self, i: int, n: int) -> None:
        """引擎进度回调：内联到统计栏并立即刷新。"""
        self.preview_bar.set_progress(T["exec_running"].format(i=i, n=n))
        self.update_idletasks()

    def _on_execute(self) -> None:
        """执行重命名：确认 → pending 落盘 → 两阶段执行 → 按结果收尾。"""
        changes = [f for f in self.files if f.new_name != f.original_name]
        if not changes:
            messagebox.showinfo(T["app_title"], T["exec_nothing"])
            return
        if not messagebox.askyesno(
            T["exec_confirm_title"], T["exec_confirm"].format(n=len(changes))
        ):
            return

        ops = [
            OperationRecord(
                orig=f.original_path,
                final=os.path.join(os.path.dirname(f.original_path), f.new_name),
            )
            for f in changes
        ]
        session = undo_stack.new_session(ops)
        undo_stack.push(session)          # 执行前落盘（pending）

        self._set_busy(True)
        try:
            result = execute_operations(
                [(op.orig, op.final) for op in ops],
                progress=self._progress_cb,
            )
        finally:
            self._set_busy(False)
            self.preview_bar.set_progress(None)

        # 执行记录状态按正向语义回写 session
        if result.success:
            for op in session.operations:
                op.state = "final"
        else:
            by_orig = {r.orig: r for r in result.records}
            for op in session.operations:
                r = by_orig.get(op.orig)
                if r:
                    op.state, op.error, op.tmp = r.state, r.error, r.tmp

        if result.success:
            session.status = "completed"
            undo_stack.push(session)
            logger.info("执行成功：%d 个文件已重命名", result.total)
            self.files.clear()            # 本批完成，列表清空收尾
            messagebox.showinfo(
                T["app_title"], T["exec_success"].format(n=result.total)
            )
        elif result.rolled_back:
            session.status = "rolled_back"
            undo_stack.push(session)
            undo_stack.discard(session.session_id)   # 净零变化，记录无意义
            messagebox.showerror(
                T["exec_fail_title"],
                T["exec_fail_rolled"].format(err=result.error),
            )
        else:
            session.status = "partial"
            undo_stack.push(session)
            # state=final 的文件实际已改名，同步列表显示
            final_by_orig = {op.orig: op for op in session.operations}
            for f in list(self.files):
                op = final_by_orig.get(f.original_path)
                if op and op.state == "final":
                    f.original_path = op.final
                    f.original_name = os.path.basename(op.final)
            detail = "\n".join(
                f"  {os.path.basename(r.orig)} → 状态 {r.state}"
                for r in result.residual
            )
            messagebox.showerror(
                T["exec_fail_title"],
                T["exec_fail_partial"].format(err=result.error, detail=detail),
            )
        self._recompute()

    def _on_undo(self) -> None:
        """撤销最近一次：completed → undoing → 成功删除 / 失败按结果回写。"""
        session = undo_stack.load_latest_undoable()
        if session is None:
            messagebox.showinfo(T["app_title"], T["undo_none"])
            return

        # 撤销前占用校验：final 在位且 orig 空闲
        for op in session.operations:
            if not os.path.exists(op.final) or os.path.exists(op.orig):
                messagebox.showerror(T["app_title"], T["undo_occupied"])
                return

        n = len(session.operations)
        if not messagebox.askyesno(T["app_title"], T["undo_confirm"].format(n=n)):
            return

        session.status = "undoing"
        undo_stack.push(session)          # 防撤销中崩溃悬挂

        self._set_busy(True)
        try:
            result = execute_operations(
                [(op.final, op.orig) for op in session.operations],
                progress=self._progress_cb,
            )
        finally:
            self._set_busy(False)
            self.preview_bar.set_progress(None)

        # 撤销状态映射回正向语义：
        #   exec "orig"（停在 pairs 源 = 正向 final 位置）-> op "final"
        #   exec "final"（停在 pairs 目标 = 正向 orig 位置）-> op "orig"
        if not result.success:
            state_map = {"orig": "final", "final": "orig"}
            by_src = {r.orig: r for r in result.records}
            for op in session.operations:
                r = by_src.get(op.final)
                if r:
                    op.state = state_map.get(r.state, r.state)
                    op.error = r.error

        if result.success:
            undo_stack.discard(session.session_id)
            logger.info("撤销成功：%d 个文件已还原", n)
            messagebox.showinfo(T["app_title"], T["undo_success"].format(n=n))
        elif result.rolled_back:
            session.status = "completed"  # 回到执行后状态，可重试
            undo_stack.push(session)
            messagebox.showerror(
                T["undo_fail_title"],
                T["undo_fail_rolled"].format(err=result.error),
            )
        else:
            session.status = "partial"
            undo_stack.push(session)
            detail = "\n".join(
                f"  {os.path.basename(r.orig)} → 状态 {r.state}"
                for r in result.residual
            )
            messagebox.showerror(
                T["undo_fail_title"],
                T["undo_fail_partial"].format(err=result.error, detail=detail),
            )
        self._recompute()

    def _startup_maintenance(self) -> None:
        """启动维护：清理探测残留、提示崩溃悬挂记录。"""
        from src.core.renamer import cleanup_probe_files

        for d in undo_stack.involved_directories():
            cleanup_probe_files(d)
        suspended = undo_stack.scan_suspended()
        if suspended:
            statuses = {s.status for s in suspended}
            messagebox.showwarning(
                T["suspended_title"],
                T["suspended_msg"].format(
                    status="/".join(sorted(statuses)), n=len(suspended)
                ),
            )

    # ------------------------------------------------------------------
    # 窗口交互
    # ------------------------------------------------------------------
    def _theme_btn_text(self) -> str:
        """根据当前主题返回切换按钮文案。"""
        current = ctk.get_appearance_mode().lower()
        return T["theme_to_light"] if current == "dark" else T["theme_to_dark"]

    def _toggle_theme(self) -> None:
        """深/浅色切换：CTk 全局换肤 + Treeview 手动适配 + 持久化。"""
        current = ctk.get_appearance_mode().lower()
        new = "light" if current == "dark" else "dark"
        ctk.set_appearance_mode(new)
        apply_treeview_style(dark=(new == "dark"))
        self.file_list.apply_status_tags(dark=(new == "dark"))
        self.theme_btn.configure(text=self._theme_btn_text())
        self.cfg["theme"] = new
        config_store.save_config(self.cfg)

    def _toggle_panel(self) -> None:
        """折叠/展开左侧规则面板；折叠后文件列表自动撑满。"""
        if self._panel_expanded:
            self.rule_panel.grid_remove()
            self.left_container.configure(width=self.STRIP_W)
            self.collapse_btn.configure(text="▶")
        else:
            self.left_container.configure(width=self.PANEL_W)
            self.rule_panel.grid()
            self.collapse_btn.configure(text="◀")
        self._panel_expanded = not self._panel_expanded

    def _on_close(self) -> None:
        """关闭窗口：保存配置后退出。"""
        config_store.save_config(self.cfg)
        self.destroy()
