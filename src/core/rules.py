"""规则链引擎：按顺序对文件名应用启用的规则。

设计要点：
- 只修改主名（stem），扩展名在 apply() 两端统一拼回；
- numbering 依赖文件序号 (index, total)，由调用方传入；
- 单条规则的参数异常（如非法正则）不抛出，保持原名并记日志，
  避免一条坏规则让整个列表崩溃。
"""

from __future__ import annotations

import re
from logging import getLogger

from src.core.models import RenameRule

logger = getLogger("RenameKit")

# 规则类型注册表（UI 添加菜单也从这里取）
RULE_TYPES: tuple[str, ...] = (
    "prefix",
    "suffix",
    "replace",
    "numbering",
    "case",
    "delete",
)


def default_params(rule_type: str) -> dict:
    """返回各规则类型的默认参数。"""
    defaults: dict[str, dict] = {
        "prefix": {"text": ""},
        "suffix": {"text": ""},
        "replace": {"find": "", "replace": "", "case_sensitive": True, "regex": False},
        "numbering": {"start": 1, "step": 1, "digits": 3, "position": "after", "separator": "_"},
        "case": {"mode": "upper"},
        "delete": {"mode": "range", "start": 0, "count": 1, "chars": ""},
    }
    return dict(defaults.get(rule_type, {}))


class RuleEngine:
    """规则链执行引擎。"""

    def __init__(self, rules: list[RenameRule] | None = None):
        self.rules = rules if rules is not None else []

    def apply(self, filename: str, index: int, total: int) -> str:
        """对单个文件名依次应用所有启用的规则。

        Args:
            filename: 原文件名（含扩展名）
            index: 当前文件序号（0 开始），供序号编号规则使用
            total: 文件总数
        Returns:
            新文件名（含扩展名）
        """
        import os

        name, ext = os.path.splitext(filename)
        for rule in self.rules:
            if not rule.enabled:
                continue
            name = self._apply_rule(rule, name, index, total)
        return name + ext

    # ------------------------------------------------------------------
    def _apply_rule(self, rule: RenameRule, name: str, index: int, total: int) -> str:
        """应用单条规则，异常时返回原名。"""
        try:
            handler = getattr(self, f"_rule_{rule.rule_type}", None)
            if handler is None:
                logger.warning("未知规则类型: %s", rule.rule_type)
                return name
            return handler(rule.params, name, index, total)
        except Exception:
            logger.exception("规则执行失败 type=%s params=%s", rule.rule_type, rule.params)
            return name

    @staticmethod
    def _rule_prefix(params: dict, name: str, index: int, total: int) -> str:
        """添加前缀。"""
        return str(params.get("text", "")) + name

    @staticmethod
    def _rule_suffix(params: dict, name: str, index: int, total: int) -> str:
        """添加后缀（主名末尾、扩展名前）。"""
        return name + str(params.get("text", ""))

    @staticmethod
    def _rule_replace(params: dict, name: str, index: int, total: int) -> str:
        """查找替换，支持普通文本与正则、大小写开关。"""
        find = str(params.get("find", ""))
        if not find:
            return name
        replace = str(params.get("replace", ""))
        case_sensitive = bool(params.get("case_sensitive", True))
        use_regex = bool(params.get("regex", False))

        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            return re.sub(find, replace, name, flags=flags)
        if case_sensitive:
            return name.replace(find, replace)
        # 非正则 + 不区分大小写：用正则转义后忽略大小写替换
        return re.sub(re.escape(find), replace.replace("\\", "\\\\"), name, flags=re.IGNORECASE)

    @staticmethod
    def _rule_numbering(params: dict, name: str, index: int, total: int) -> str:
        """序号编号：起始值 + 序号×步长，按位数补零。"""
        start = int(params.get("start", 1))
        step = int(params.get("step", 1))
        digits = max(1, int(params.get("digits", 3)))
        position = str(params.get("position", "after"))
        separator = str(params.get("separator", "_"))

        value = start + index * step
        num = str(value).zfill(digits)
        if position == "before":
            return num + separator + name
        return name + separator + num

    @staticmethod
    def _rule_case(params: dict, name: str, index: int, total: int) -> str:
        """大小写转换。"""
        mode = str(params.get("mode", "upper"))
        if mode == "lower":
            return name.lower()
        if mode == "title":
            return name.capitalize()
        return name.upper()

    @staticmethod
    def _rule_delete(params: dict, name: str, index: int, total: int) -> str:
        """删除字符：按区间删除，或删除指定字符集合。"""
        mode = str(params.get("mode", "range"))
        if mode == "chars":
            chars = set(str(params.get("chars", "")))
            if not chars:
                return name
            return "".join(ch for ch in name if ch not in chars)
        # mode == "range"
        start = int(params.get("start", 0))
        count = max(0, int(params.get("count", 1)))
        start = max(0, start)
        return name[:start] + name[start + count:]
