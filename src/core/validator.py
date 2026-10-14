"""校验器：新文件名的冲突与合法性检查（阶段 3）。

检查项（对应文档 4.4 + 阶段 4 阻断点补充）：
1. 同目录内新文件名重复（批内冲突，黄色）
2. 与磁盘已有文件重名且占用者不让位（外部冲突，红色）
   —— 占用者在批内且会被改走时不标冲突，由阶段 4 临时名中转执行
3. 非法字符 \\ / : * ? " < > |、空名、首尾空白、尾点/尾空格
4. Windows 保留名（CON/PRN/AUX/NUL/COM1-9/LPT1-9，含扩展形式）
5. 目标完整路径超过 Windows 260 字符限制

校验直接就地写回 FileItem.status，返回问题行数。
状态：ok / unchanged / conflict（批内，黄）/ disk_conflict（外部，红）
     / invalid（红）
"""

from __future__ import annotations

import os
from collections import Counter

from src.core.models import FileItem

ILLEGAL_CHARS = set('\\/:*?"<>|')
MAX_PATH_LEN = 260

# Windows 设备保留名：按“第一个点前的部分”匹配，CON.txt 同样非法
RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

# 问题状态（UI 标红/标黄，均计入统计并阻止执行）
ISSUE_STATUSES = ("conflict", "disk_conflict", "invalid")


def validate(items: list[FileItem]) -> int:
    """就地设置每个 FileItem 的 status，返回问题行数。

    Args:
        items: 已完成 new_name 计算的文件列表
    Returns:
        status 为 conflict / disk_conflict / invalid 的行数
    """
    # 冲突以“同目录 + 同名”为准（不同目录同名互不影响）；
    # Windows 不区分大小写，按小写统计
    counts: Counter[tuple[str, str]] = Counter(
        (os.path.normcase(os.path.dirname(f.original_path)), f.new_name.lower())
        for f in items
    )
    # 批内原始路径索引：判断磁盘占用者是否会被改走
    batch_by_path = {
        os.path.normcase(os.path.abspath(f.original_path)): f for f in items
    }

    issues = 0
    for item in items:
        item.status = _validate_one(item, counts, batch_by_path)
        if item.status in ISSUE_STATUSES:
            issues += 1
    return issues


def _validate_one(
    item: FileItem,
    counts: Counter,
    batch_by_path: dict[str, FileItem],
) -> str:
    """单个文件的校验，返回状态字符串。"""
    name = item.new_name

    # 1) 非法字符 / 空名 / 首尾空白
    if not name or name != name.strip() or name in (".", ".."):
        return "invalid"
    if any(ch in ILLEGAL_CHARS for ch in name):
        return "invalid"

    # 2) 尾点/尾空格（全名，或主名以 . / 空格 结尾）
    if name.endswith((".", " ")):
        return "invalid"
    stem = os.path.splitext(name)[0]
    if stem.endswith((".", " ")):
        return "invalid"

    # 3) Windows 保留名（第一个点前的部分，大小写不敏感）
    head = name.split(".", 1)[0].upper()
    if head in RESERVED_NAMES:
        return "invalid"

    # 4) 目标完整路径长度（Windows MAX_PATH = 260）
    target = os.path.join(os.path.dirname(item.original_path), name)
    if len(target) >= MAX_PATH_LEN:
        return "invalid"

    # 5) 同目录批内重复 -> 批内冲突（黄色）
    dir_key = os.path.normcase(os.path.dirname(item.original_path))
    if counts[(dir_key, name.lower())] > 1:
        return "conflict"

    # 6) 磁盘占用检查
    if os.path.exists(target):
        target_key = os.path.normcase(os.path.abspath(target))
        self_key = os.path.normcase(os.path.abspath(item.original_path))
        if target_key != self_key:
            occupant = batch_by_path.get(target_key)
            if occupant is None:
                # 占用者不在批内 -> 外部冲突（红色）
                return "disk_conflict"
            # 占用者在批内：会被改走（new != original）则放行，
            # 由阶段 4 临时名中转处理 A→B、B→C 循环
            if occupant.original_name == occupant.new_name:
                # 占用者不让位：本文件 new_name == 占用者名字，
                # 已在第 5 步批内重复处标为 conflict；此处兜底
                return "conflict"

    # 7) 无变化
    if name == item.original_name:
        return "unchanged"
    return "ok"
