"""数据模型：FileItem / RenameRule / OperationRecord / RenameSession。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FileItem:
    """单个待重命名文件。"""

    original_path: str      # 原完整路径
    original_name: str      # 原文件名（含扩展名）
    new_name: str = ""      # 规则链计算后的新文件名
    # ok / unchanged / conflict（批内，黄）/ disk_conflict（外部，红）/ invalid（红）
    status: str = "ok"


@dataclass
class RenameRule:
    """一条重命名规则。"""

    rule_type: str                  # prefix/suffix/replace/numbering/case/delete
    params: dict = field(default_factory=dict)
    enabled: bool = True


@dataclass
class OperationRecord:
    """单个文件的改名操作及其实时状态（undo 记录的最小单元）。"""

    orig: str                      # 原完整路径
    final: str                     # 目标完整路径
    tmp: str | None = None         # 阶段一临时路径（进入阶段一后赋值）
    # orig=未动/已回滚 | tmp=停在临时名 | final=停在目标名 | lost=丢失 | conflict=多处并存
    state: str = "orig"
    error: str | None = None       # 该文件的失败原因

    def to_dict(self) -> dict:
        return {
            "orig": self.orig, "final": self.final, "tmp": self.tmp,
            "state": self.state, "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OperationRecord":
        return cls(
            orig=d["orig"], final=d["final"], tmp=d.get("tmp"),
            state=d.get("state", "orig"), error=d.get("error"),
        )


@dataclass
class RenameSession:
    """一次执行/撤销会话（undo 记录本体）。

    status 流转：
        正向: pending -> completed | rolled_back(删除) | partial
        撤销: completed -> undoing -> 删除 | completed | partial
        悬挂: pending / undoing（进程中断，启动扫描提示）
    """

    session_id: str                       # uuid4 hex
    timestamp: str                        # ISO 8601
    status: str = "pending"
    error: str | None = None
    operations: list[OperationRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "error": self.error,
            "operations": [op.to_dict() for op in self.operations],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RenameSession":
        return cls(
            session_id=d["session_id"],
            timestamp=d["timestamp"],
            status=d.get("status", "pending"),
            error=d.get("error"),
            operations=[OperationRecord.from_dict(o) for o in d.get("operations", [])],
        )
