"""
Skill 字段枚举。

定义 Skill 的所有字段及其含义、解析规则。
每个字段对应 Markdown 中的一个 section，解析器按此规则提取内容。
"""

from enum import Enum


class SkillField(str, Enum):
    """
    Skill 字段枚举。

    每个字段对应 Skill Markdown 文档中的一个 section。
    解析器按此规则从 Markdown 中提取对应字段内容。

    字段含义：
    - TITLE: Skill 标题，唯一标识之外的人类可读名称
    - DESCRIPTION: 简短描述，一句话说明 Skill 用途，用于 Agent 快速理解
    - CONTENT: Skill 核心内容（提示词模板、代码片段等），Agent 实际执行的逻辑
    - PARAMETERS: Skill 接受的参数定义，JSON Schema 格式
    - EXAMPLES: 使用示例，展示 Skill 的典型用法
    - CONSTRAINTS: 约束条件，说明 Skill 的使用限制和注意事项
    - METADATA: 附加元数据（版本、作者、标签等）
    """

    TITLE = "title"
    """Skill 标题。用于界面展示，不参与 Agent 调用。"""

    DESCRIPTION = "description"
    """简短描述。Agent 通过此字段快速判断 Skill 用途。"""

    CONTENT = "content"
    """
    Skill 核心内容。

    规则：
    - 可以是多轮对话模板
    - 可以是代码片段
    - 可以是结构化指令
    - Agent 实际执行时读取此字段
    """

    PARAMETERS = "parameters"
    """
    参数定义。

    规则：
    - 格式为 JSON Schema
    - 定义 Skill 接受的输入参数类型和约束
    - 用于验证和文档生成
    """

    EXAMPLES = "examples"
    """
    使用示例。

    规则：
    - 格式为 Markdown 列表
    - 每个示例包含：场景描述 + 预期输入 + 预期输出
    - 用于 Agent 理解和测试
    """

    CONSTRAINTS = "constraints"
    """
    约束条件。

    规则：
    - 格式为 Markdown 列表
    - 说明 Skill 的使用限制、注意事项、边界情况
    - Agent 决策时参考此字段
    """

    METADATA = "metadata"
    """
    附加元数据。

    规则：
    - 格式为 JSON 或 Markdown 表格
    - 包含：version、author、tags、created_at 等
    - 用于管理和追踪
    """

    @classmethod
    def values(cls) -> list[str]:
        """返回所有字段值列表。"""
        return [f.value for f in cls]

    @classmethod
    def lite_fields(cls) -> list[str]:
        """返回摘要字段列表（不含 content）。"""
        return [cls.TITLE.value, cls.DESCRIPTION.value, cls.PARAMETERS.value]

    @classmethod
    def full_fields(cls) -> list[str]:
        """返回完整字段列表。"""
        return cls.values()
