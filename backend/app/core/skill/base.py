"""
Skill 数据模型。

定义 Skill 的数据结构和字段规范。
Skill 存储在数据库中，通过 load_skill / load_skill_lite 工具按需加载。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.core.skill.field import SkillField


class Skill(BaseModel):
    """
    Skill 数据模型。

    字段说明见 SkillField 枚举。

    示例 Markdown 格式：
        # Skill Title

        ## description
        这是一个用于...的 Skill。

        ## content
        你是一个专业的...，请根据用户输入...

        ## parameters
        ```json
        {
          "type": "object",
          "properties": {
            "input": {"type": "string", "description": "用户输入"}
          }
        }
        ```

        ## examples
        - 示例1: 输入... 输出...

        ## constraints
        - 不要...
        - 必须...
    """

    name: str = Field(..., description="唯一标识，Agent 通过此名称引用 Skill")
    title: Optional[str] = Field(None, description="Skill 标题，用于界面展示")
    description: str = Field(default="", description="简短描述，一句话说明用途")
    content: Optional[str] = Field(None, description="核心内容，Agent 实际执行的逻辑")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="参数 JSON Schema",
    )
    examples: List[str] = Field(default_factory=list, description="使用示例")
    constraints: List[str] = Field(default_factory=list, description="约束条件")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="附加元数据（version、author、tags 等）",
    )

    model_config = {"extra": "allow"}

    def get_lite_fields(self) -> Dict[str, Any]:
        """获取摘要字段（不含 content）。"""
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "parameters": self.parameters,
        }

    def get_fields(
        self,
        fields: Optional[List[SkillField]] = None,
    ) -> Dict[str, Any]:
        """
        按字段过滤返回。

        Args:
            fields: 要返回的字段列表，None 则返回全部

        Returns:
            字段值字典
        """
        data = self.model_dump()
        if fields is None:
            return data

        result = {}
        for f in fields:
            if f.value in data:
                result[f.value] = data[f.value]
        return result


class SkillLite(BaseModel):
    """Skill 摘要。用于 Agent 创建时注入基本信息到提示词，不含 content。"""

    name: str
    title: Optional[str] = None
    description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
