"""规则编辑面板：规则卡片的增删、启停、排序与参数编辑。"""

from __future__ import annotations

from tkinter import Menu

import customtkinter as ctk

from src.core.models import RenameRule
from src.core.rules import RULE_TYPES, default_params
from src.utils.i18n import T
from src.utils.logger import get_logger

logger = get_logger()

# 规则类型 -> 文案键
_TYPE_LABEL_KEYS = {
    "prefix": "rule_prefix",
    "suffix": "rule_suffix",
    "replace": "rule_replace",
    "numbering": "rule_numbering",
    "case": "rule_case",
    "delete": "rule_delete",
}


class RuleCard(ctk.CTkFrame):
    """单条规则卡片：启停勾选 + 参数编辑 + 上移/下移/删除。"""

    def __init__(self, master, rule: RenameRule, panel: "RulePanel"):
        super().__init__(master, corner_radius=8)
        self.rule = rule
        self.panel = panel
        self.grid_columnconfigure(1, weight=1)

        # ---- 第一行：勾选 + 类型名 + 操作按钮 ----
        self.enabled_var = ctk.BooleanVar(value=rule.enabled)
        self.check = ctk.CTkCheckBox(
            self, text="", width=24, checkbox_width=18, checkbox_height=18,
            command=self._on_toggle,
        )
        self.check.grid(row=0, column=0, padx=(8, 2), pady=(6, 0), sticky="nw")
        self.check.select() if rule.enabled else self.check.deselect()

        ctk.CTkLabel(
            self,
            text=T[_TYPE_LABEL_KEYS.get(rule.rule_type, "rule_prefix")],
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=1, padx=4, pady=(6, 0), sticky="w")

        btn_kw = dict(
            width=24, height=24, corner_radius=4, fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"), font=ctk.CTkFont(size=12),
        )
        ctk.CTkButton(self, text="↑", command=lambda: panel.move(self.rule, -1), **btn_kw)\
            .grid(row=0, column=2, padx=1, pady=(6, 0))
        ctk.CTkButton(self, text="↓", command=lambda: panel.move(self.rule, +1), **btn_kw)\
            .grid(row=0, column=3, padx=1, pady=(6, 0))
        ctk.CTkButton(
            self, text="✕", command=lambda: panel.remove(self.rule),
            fg_color=("gray75", "gray30"), hover_color=("#c0392b", "#a93226"), **{
                k: v for k, v in btn_kw.items() if k not in ("fg_color", "hover_color")
            },
        ).grid(row=0, column=4, padx=(1, 8), pady=(6, 0))

        # ---- 第二行：参数编辑区 ----
        self.param_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.param_frame.grid(row=1, column=0, columnspan=5, sticky="ew", padx=8, pady=(4, 8))
        self._build_params()

    # ------------------------------------------------------------------
    def _on_toggle(self) -> None:
        self.rule.enabled = bool(self.enabled_var.get())
        self.panel.on_change()

    def _entry(self, parent, key: str, placeholder: str, width: int = 110,
               numeric: bool = False) -> ctk.CTkEntry:
        """创建参数输入框，改动即写回 rule.params。"""
        initial = str(self.rule.params.get(key, ""))
        entry = ctk.CTkEntry(parent, width=width, height=28, placeholder_text=placeholder)
        entry.insert(0, initial)

        def _sync(_event=None):
            raw = entry.get()
            if numeric:
                try:
                    self.rule.params[key] = int(raw)
                except ValueError:
                    self.rule.params[key] = raw  # 输入过程中暂存，引擎侧兜底
            else:
                self.rule.params[key] = raw
            self.panel.on_change()

        entry.bind("<KeyRelease>", _sync, add="+")
        return entry

    def _checkbox(self, parent, key: str, label: str) -> ctk.CTkCheckBox:
        var = ctk.BooleanVar(value=bool(self.rule.params.get(key, False)))
        cb = ctk.CTkCheckBox(
            parent, text=label, variable=var, height=24,
            checkbox_width=16, checkbox_height=16, font=ctk.CTkFont(size=12),
        )

        def _sync():
            self.rule.params[key] = bool(var.get())
            self.panel.on_change()

        cb.configure(command=_sync)
        cb.select() if var.get() else cb.deselect()
        return cb

    def _option(self, parent, key: str, choices: list[tuple[str, str]],
                width: int = 96) -> ctk.CTkOptionMenu:
        """创建下拉框；choices = [(显示文本, 存储值), ...]。"""
        label_of = {v: lab for lab, v in choices}
        current = str(self.rule.params.get(key, choices[0][1]))
        menu = ctk.CTkOptionMenu(
            parent, values=[lab for lab, _ in choices], width=width, height=28,
            font=ctk.CTkFont(size=12), dynamic_resizing=False,
        )
        menu.set(label_of.get(current, choices[0][0]))

        def _sync(selected_label: str):
            for lab, val in choices:
                if lab == selected_label:
                    self.rule.params[key] = val
                    break
            self.panel.on_change()

        menu.configure(command=_sync)
        return menu

    # ------------------------------------------------------------------
    def _build_params(self) -> None:
        """按规则类型搭建参数编辑控件。"""
        f = self.param_frame
        t = self.rule.rule_type

        if t in ("prefix", "suffix"):
            f.grid_columnconfigure(0, weight=1)
            self._entry(f, "text", T["param_text"], width=200)\
                .grid(row=0, column=0, sticky="ew")

        elif t == "replace":
            f.grid_columnconfigure(0, weight=1)
            self._entry(f, "find", T["param_find"], width=200)\
                .grid(row=0, column=0, sticky="ew", pady=(0, 4))
            self._entry(f, "replace", T["param_replace"], width=200)\
                .grid(row=1, column=0, sticky="ew")
            self._checkbox(f, "case_sensitive", T["param_case_sensitive"])\
                .grid(row=2, column=0, sticky="w", pady=(4, 0))
            self._checkbox(f, "regex", T["param_regex"])\
                .grid(row=2, column=0, sticky="w", padx=(140, 0), pady=(4, 0))

        elif t == "numbering":
            row1 = ctk.CTkFrame(f, fg_color="transparent")
            row1.grid(row=0, column=0, sticky="ew")
            row1.grid_columnconfigure((0, 1, 2), weight=1)
            self._entry(row1, "start", T["param_start"], width=56, numeric=True)\
                .grid(row=0, column=0, sticky="ew", padx=(0, 4))
            self._entry(row1, "step", T["param_step"], width=56, numeric=True)\
                .grid(row=0, column=1, sticky="ew", padx=4)
            self._entry(row1, "digits", T["param_digits"], width=56, numeric=True)\
                .grid(row=0, column=2, sticky="ew", padx=(4, 0))

            row2 = ctk.CTkFrame(f, fg_color="transparent")
            row2.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            row2.grid_columnconfigure(1, weight=1)
            self._option(row2, "position", [(T["pos_before"], "before"),
                                            (T["pos_after"], "after")], width=64)\
                .grid(row=0, column=0, padx=(0, 4))
            self._entry(row2, "separator", T["param_separator"], width=64)\
                .grid(row=0, column=1, sticky="ew")

        elif t == "case":
            self._option(f, "mode", [
                (T["case_upper"], "upper"),
                (T["case_lower"], "lower"),
                (T["case_title"], "title"),
            ], width=110).grid(row=0, column=0, sticky="w")

        elif t == "delete":
            mode_label_of = {"range": T["del_range"], "chars": T["del_chars"]}
            current_mode = str(self.rule.params.get("mode", "range"))
            mode_menu = ctk.CTkOptionMenu(
                f, values=list(mode_label_of.values()), width=120, height=28,
                font=ctk.CTkFont(size=12), dynamic_resizing=False,
            )
            mode_menu.set(mode_label_of.get(current_mode, T["del_range"]))
            mode_menu.grid(row=0, column=0, sticky="w")

            def _mode_sync(label: str):
                for val, lab in mode_label_of.items():
                    if lab == label:
                        self.rule.params["mode"] = val
                        break
                self._sync_delete_mode()
                self.panel.on_change()

            mode_menu.configure(command=_mode_sync)
            # 两种模式的输入都建好，按当前模式显隐
            self._range_row = ctk.CTkFrame(f, fg_color="transparent")
            self._range_row.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            self._range_row.grid_columnconfigure((0, 1), weight=1)
            self._entry(self._range_row, "start", T["param_start"], width=56, numeric=True)\
                .grid(row=0, column=0, sticky="ew", padx=(0, 4))
            self._entry(self._range_row, "count", "长度", width=56, numeric=True)\
                .grid(row=0, column=1, sticky="ew", padx=(4, 0))
            self._chars_row = ctk.CTkFrame(f, fg_color="transparent")
            self._chars_row.grid(row=1, column=0, sticky="ew", pady=(4, 0))
            self._chars_row.grid_columnconfigure(0, weight=1)
            self._entry(self._chars_row, "chars", T["param_chars"], width=140)\
                .grid(row=0, column=0, sticky="ew")
            self._sync_delete_mode()

    def _sync_delete_mode(self) -> None:
        """按 delete 规则的模式显示对应输入行。"""
        mode = str(self.rule.params.get("mode", "range"))
        if mode == "chars":
            self._range_row.grid_remove()
            self._chars_row.grid()
        else:
            self._chars_row.grid_remove()
            self._range_row.grid()


class RulePanel(ctk.CTkFrame):
    """左侧规则面板内容：添加按钮 + 可滚动规则卡片列表。"""

    def __init__(self, master, rules: list[RenameRule], on_change, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.rules = rules
        self.on_change = on_change

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 顶部：添加规则按钮（弹出类型菜单）
        self.add_btn = ctk.CTkButton(self, text=T["add_rule"], height=34,
                                     command=self._show_add_menu)
        self.add_btn.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        self._menu: Menu | None = None

        # 规则卡片列表
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                             label_text="", corner_radius=6)
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(2, 8))
        self.scroll.grid_columnconfigure(0, weight=1)

        # 空态占位
        self.empty_label = ctk.CTkLabel(
            self, text=T["empty_rules"],
            text_color=("gray40", "gray60"), font=ctk.CTkFont(size=13),
            justify="center",
        )

        self.rebuild()

    # ------------------------------------------------------------------
    def _show_add_menu(self) -> None:
        """在按钮下方弹出规则类型菜单。"""
        if self._menu is not None:
            self._menu.destroy()
        self._menu = Menu(self, tearoff=0)
        for rule_type in RULE_TYPES:
            label = T[_TYPE_LABEL_KEYS[rule_type]]
            self._menu.add_command(
                label=label,
                command=lambda rt=rule_type: self.add(rt),
            )
        x = self.add_btn.winfo_rootx()
        y = self.add_btn.winfo_rooty() + self.add_btn.winfo_height()
        self._menu.tk_popup(x, y)

    # ------------------------------------------------------------------
    def add(self, rule_type: str) -> None:
        """追加一条默认参数的新规则。"""
        self.rules.append(RenameRule(rule_type=rule_type, params=default_params(rule_type)))
        logger.info("添加规则 %s", rule_type)
        self.rebuild()
        self.on_change()

    def remove(self, rule: RenameRule) -> None:
        """删除指定规则。"""
        if rule in self.rules:
            self.rules.remove(rule)
            self.rebuild()
            self.on_change()

    def move(self, rule: RenameRule, direction: int) -> None:
        """上移(-1)/下移(+1)指定规则。"""
        i = self.rules.index(rule)
        j = i + direction
        if 0 <= j < len(self.rules):
            self.rules[i], self.rules[j] = self.rules[j], self.rules[i]
            self.rebuild()
            self.on_change()

    def rebuild(self) -> None:
        """按 self.rules 重建全部卡片。"""
        for child in self.scroll.winfo_children():
            child.destroy()
        if not self.rules:
            self.empty_label.place(relx=0.5, rely=0.3, anchor="center")
            return
        self.empty_label.place_forget()
        for idx, rule in enumerate(self.rules):
            card = RuleCard(self.scroll, rule, self)
            card.grid(row=idx, column=0, sticky="ew", padx=4, pady=(0, 6))
