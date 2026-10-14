"""重命名执行引擎：两阶段临时名中转 + 全原子回滚 + 状态探测。

设计要点见阶段 4 方案：
- 阶段一：全部 orig -> 唯一临时名；阶段二：tmp -> final，天然化解
  A→B、B→C 循环与 case-only 改名；
- 任何失败立即停止并逆序回滚，回滚后 refresh_states 落盘真实状态；
- 引擎不感知 undo（不写记录），只操作文件系统与传入的 session 对象；
- 目录级火绒探测（每目录一次），结果只影响走 rename 还是复制路径，
  safe_rename 的回退永远保留。
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Callable

from src.core.models import OperationRecord
from src.utils.fileops import safe_rename, set_hidden
from src.utils.logger import get_logger

logger = get_logger()

# 探测文件命名：._rk_probe_{8hex}_（及改名后的 ..._r），清理时严格匹配
_PROBE_RE = re.compile(r"^\._rk_probe_[0-9a-f]{8}_(_r)?$")
# 临时文件命名：__RKTMP_{12hex}__{ext}
_TMP_RE = re.compile(r"^__RKTMP_[0-9a-f]{12}__")


# ----------------------------------------------------------------------
# 状态分类
# ----------------------------------------------------------------------
def classify_state(orig: bool, tmp: bool, final: bool) -> str:
    """按三个路径的存在性判定文件实际状态（纯函数，可表驱动单测）。

    orig✓ tmp✗ final✗ → orig    回滚成功/未动
    orig✗ tmp✓ final✗ → tmp     回滚失败，停在临时名
    orig✗ tmp✗ final✓ → final   停在目标名（回滚 final→orig 也失败）
    orig✗ tmp✗ final✗ → lost    三方全无，需人工
    其余组合           → conflict 半回滚/外界干扰，需人工
    """
    if orig and not tmp and not final:
        return "orig"
    if not orig and tmp and not final:
        return "tmp"
    if not orig and not tmp and final:
        return "final"
    if not orig and not tmp and not final:
        return "lost"
    return "conflict"


def refresh_states(records: list[OperationRecord]) -> None:
    """对每条记录做 exists 探测，就地更新 state。"""
    for rec in records:
        rec.state = classify_state(
            os.path.exists(rec.orig),
            bool(rec.tmp) and os.path.exists(rec.tmp),
            os.path.exists(rec.final),
        )


# ----------------------------------------------------------------------
# 目录探测（火绒）
# ----------------------------------------------------------------------
def cleanup_probe_files(directory: str) -> int:
    """清理本程序命名的历史探测残留（严格正则，绝不碰用户文件）。"""
    removed = 0
    try:
        for name in os.listdir(directory):
            if _PROBE_RE.match(name):
                try:
                    os.remove(os.path.join(directory, name))
                    removed += 1
                except OSError:
                    pass
    except OSError:
        pass
    return removed


def probe_rename_capability(directory: str) -> bool:
    """探测目录内 os.rename 是否可用（每目录一次，结果缓存）。

    探测文件：._rk_probe_{8hex}_，创建后设隐藏属性，试改名为 ..._r，
    无论成败都清理干净（含该目录的历史残留）。
    """
    cleanup_probe_files(directory)
    token = uuid.uuid4().hex[:8]
    probe = os.path.join(directory, f"._rk_probe_{token}_")
    probe2 = os.path.join(directory, f"._rk_probe_{token}_r")
    try:
        with open(probe, "wb"):
            pass
        set_hidden(probe)
        os.rename(probe, probe2)
        return True
    except OSError:
        return False
    finally:
        for p in (probe, probe2):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass


def _make_tmp(orig: str) -> str:
    """生成批次内与磁盘上都唯一的临时路径（保留原扩展名）。"""
    directory, ext = os.path.split(orig)[0], os.path.splitext(orig)[1]
    while True:
        cand = os.path.join(directory, f"__RKTMP_{uuid.uuid4().hex[:12]}__{ext}")
        if not os.path.exists(cand):
            return cand


# ----------------------------------------------------------------------
# 执行结果
# ----------------------------------------------------------------------
@dataclass
class ExecutionResult:
    success: bool
    total: int                      # 参与执行的操作数
    executed: int                   # 到达 final 的数量
    rolled_back: bool = True        # 失败后是否回滚完整
    error: str | None = None        # 失败描述（含位置）
    residual: list[OperationRecord] = field(default_factory=list)  # state != orig 的记录
    records: list[OperationRecord] = field(default_factory=list)   # 全部执行记录（含状态）


# ----------------------------------------------------------------------
# 主执行流程
# ----------------------------------------------------------------------
def execute_operations(
    pairs: list[tuple[str, str]],
    progress: Callable[[int, int], None] | None = None,
) -> ExecutionResult:
    """两阶段执行批量改名（失败即停、全量回滚）。

    引擎不感知 undo：只操作 pairs 与自建 records，状态回写由调用方
    按方向映射到 RenameSession（正向/撤销共用本函数）。

    Args:
        pairs: [(src, dst), ...]
        progress: 每完成一步回调 (已完成数, 总数)，用于 UI 进度刷新
    Returns:
        ExecutionResult；不抛异常（失败以 success=False 表达）
    """
    records = [OperationRecord(orig=o, final=f) for o, f in pairs]
    total = len(records)
    if total == 0:
        return ExecutionResult(success=True, total=0, executed=0, records=records)

    # 目录 rename 能力探测（火绒），False 的目录直接走复制路径
    capability: dict[str, bool] = {}

    def dir_ok(path: str) -> bool:
        d = os.path.dirname(path)
        if d not in capability:
            capability[d] = probe_rename_capability(d)
            logger.info("目录 rename 能力探测: %s -> %s", d, capability[d])
        return capability[d]

    # ---------- 阶段一：全部 -> 临时名 ----------
    phase1: list[int] = []           # 已到 tmp 的记录下标
    for i, rec in enumerate(records):
        try:
            rec.tmp = _make_tmp(rec.orig)
            safe_rename(rec.orig, rec.tmp, rename_preferred=dir_ok(rec.orig))
            rec.state = "tmp"
            rec.error = None
            phase1.append(i)
        except Exception as e:
            rec.error = str(e)
            logger.warning("阶段一失败 #%d %s: %s", i + 1, rec.orig, e)
            residual = _rollback(records, phase1, phase2=[], dir_ok=dir_ok)
            return _fail_result(records, total, len(phase1), i + 1, str(e), residual)
        if progress:
            progress(i + 1, total)

    # ---------- 阶段二：临时名 -> 目标名 ----------
    phase2: list[int] = []           # 已到 final 的记录下标
    for i, rec in enumerate(records):
        try:
            if os.path.exists(rec.final):
                raise FileExistsError(f"目标已被占用: {rec.final}")
            safe_rename(rec.tmp, rec.final, rename_preferred=dir_ok(rec.final))
            rec.state = "final"
            phase2.append(i)
        except Exception as e:
            rec.error = str(e)
            logger.warning("阶段二失败 #%d %s: %s", i + 1, rec.final, e)
            residual = _rollback(records, phase1, phase2, dir_ok=dir_ok)
            return _fail_result(records, total, len(phase2), i + 1, str(e), residual)
        if progress:
            progress(i + 1, total)

    # 成功路径不调用 refresh_states：循环改名时 orig/final 互被他人占据，
    # exists 探测会误判；state 已由阶段二逐条置为 final，直接可信。
    return ExecutionResult(
        success=True, total=total, executed=total, rolled_back=True, records=records
    )


def _rollback(
    records: list[OperationRecord],
    phase1: list[int],
    phase2: list[int],
    dir_ok: Callable[[str], bool],
) -> list[OperationRecord]:
    """逆序回滚：final→orig，然后 tmp→orig。回滚后刷新状态，返回残留记录。

    合法性：阶段一已把参与文件的 orig 位置全部腾空，回滚目标不碰撞。
    单点回滚失败不中断其余回滚（尽力恢复 + 状态落盘）。
    """
    # 阶段二完成的：final -> orig（逆序）
    for i in reversed(phase2):
        rec = records[i]
        try:
            safe_rename(rec.final, rec.orig, rename_preferred=dir_ok(rec.orig))
        except Exception as e:
            logger.error("回滚(final→orig)失败 %s: %s", rec.final, e)
    # 阶段一完成但阶段二未成的：tmp -> orig（逆序）
    in_phase2 = set(phase2)
    for i in reversed(phase1):
        if i in in_phase2:
            continue
        rec = records[i]
        try:
            safe_rename(rec.tmp, rec.orig, rename_preferred=dir_ok(rec.orig))
        except Exception as e:
            logger.error("回滚(tmp→orig)失败 %s: %s", rec.tmp, e)
    refresh_states(records)
    return [r for r in records if r.state != "orig"]


def _fail_result(
    records: list[OperationRecord],
    total: int,
    executed: int,
    fail_index: int,
    error: str,
    residual: list[OperationRecord],
) -> ExecutionResult:
    msg = f"第 {fail_index}/{total} 个失败: {error}"
    if residual:
        msg += f"；回滚后仍有 {len(residual)} 个文件有残留"
    else:
        msg += "；已全部回滚，文件未发生任何变化"
    return ExecutionResult(
        success=False,
        total=total,
        executed=executed,
        rolled_back=not residual,
        error=msg,
        residual=residual,
        records=records,
    )
