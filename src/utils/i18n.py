"""界面文案表（中英文预留，当前仅中文）。

阶段 5 之后可扩展英文词条，按语言键取用。
"""

from __future__ import annotations

T: dict[str, str] = {
    # 标题栏
    "app_title": "RenameKit",
    "theme_to_light": "切换浅色",
    "theme_to_dark": "切换深色",
    "about": "关于",
    "github": "GitHub",
    "coming_soon": "该功能即将上线，敬请期待。",
    "about_text": "RenameKit 0.1.0（开发中）\n开源免费的 Windows 批量文件重命名工具。\nGitHub 主页即将上线。",
    "github_text": "GitHub 仓库地址即将上线。",

    # 规则面板
    "rules_header": "规则链",
    "add_rule": "+ 添加规则",
    "empty_rules": "还没有规则\n点击「+ 添加规则」开始",
    "rules_coming": "规则引擎将在下一阶段实现，敬请期待。",
    "move_up": "上移",
    "move_down": "下移",
    "delete_rule": "删除此规则",

    # 规则类型
    "rule_prefix": "添加前缀",
    "rule_suffix": "添加后缀",
    "rule_replace": "查找替换",
    "rule_numbering": "序号编号",
    "rule_case": "大小写转换",
    "rule_delete": "删除字符",

    # 规则参数
    "param_text": "内容",
    "param_find": "查找",
    "param_replace": "替换为",
    "param_case_sensitive": "区分大小写",
    "param_regex": "正则",
    "param_start": "起始",
    "param_step": "步长",
    "param_digits": "位数",
    "param_position": "位置",
    "param_separator": "连接符",
    "param_mode": "模式",
    "param_chars": "字符",
    "pos_before": "前",
    "pos_after": "后",
    "case_upper": "全大写",
    "case_lower": "全小写",
    "case_title": "首字母大写",
    "del_range": "按位置删除",
    "del_chars": "删除指定字符",

    # 文件列表
    "col_original": "原文件名",
    "col_new": "新文件名",
    "empty_files": "拖拽文件或文件夹到这里\n或点击下方按钮添加",
    "add_files": "添加文件",
    "add_folder": "添加文件夹",
    "clear_list": "清空列表",
    "file_ops_coming": "文件导入功能将在下一阶段实现。",
    "include_subdirs": "包含子目录",
    "select_files": "选择要重命名的文件",
    "select_folder": "选择文件夹",

    # 底部操作栏
    "stats_zero": "共 0 个文件",
    "undo": "撤销上次",
    "execute": "执行重命名",

    # 执行与撤销（阶段 4）
    "exec_confirm_title": "确认重命名",
    "exec_confirm": "即将重命名 {n} 个文件。\n操作可通过「撤销上次」一键还原，继续吗？",
    "exec_success": "成功重命名 {n} 个文件。",
    "exec_fail_title": "执行失败",
    "exec_fail_rolled": "重命名执行失败：\n{err}\n\n已回滚全部改动，文件未发生任何变化。",
    "exec_fail_partial": "重命名执行失败：\n{err}\n\n回滚存在残留，以下文件当前状态：\n{detail}\n\n完整记录：%APPDATA%\\RenameKit\\undo",
    "exec_running": "正在执行… {i}/{n}",
    "exec_nothing": "没有需要重命名的文件（新旧文件名相同）。",
    "undo_confirm": "撤销上一次重命名操作（{n} 个文件）？",
    "undo_success": "已撤销 {n} 个文件的重命名。",
    "undo_none": "没有可撤销的操作。",
    "undo_fail_title": "撤销失败",
    "undo_fail_rolled": "撤销失败：\n{err}\n\n已恢复到执行后的状态，可稍后重试。",
    "undo_fail_partial": "撤销失败且有残留：\n{err}\n\n以下文件当前状态：\n{detail}\n\n完整记录：%APPDATA%\\RenameKit\\undo",
    "undo_occupied": "撤销被拒绝：原位置已被其他文件占用。",
    "suspended_title": "检测到中断的操作",
    "suspended_msg": "上次执行/撤销未正常结束（{status} 共 {n} 条记录）。\n请人工核对相关文件状态，必要时在\n%APPDATA%\\RenameKit\\undo 查看记录。",

    # 折叠
    "collapse_panel": "折叠规则面板",
    "expand_panel": "展开规则面板",
}
