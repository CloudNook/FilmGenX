"""
Supervisor 与 SubAgent 的 session 关联管理。
"""

from typing import Dict, Optional


class SupervisorSession:
    """
    管理 Supervisor 与 SubAgent 的 session 关联。

    Supervisor 拥有独立的 supervisor_session_id。
    每个 SubAgent 也有自己的 sub_session_id，通过此对象记录关联关系。
    """

    def __init__(self, supervisor_session_id: str):
        self.supervisor_session_id = supervisor_session_id
        self._sub_sessions: Dict[str, str] = {}

    def register_sub_session(self, sub_agent_name: str, sub_session_id: str) -> None:
        """记录一个 SubAgent 的 session_id。"""
        self._sub_sessions[sub_agent_name] = sub_session_id

    def get_sub_session(self, sub_agent_name: str) -> Optional[str]:
        """获取指定 SubAgent 的 session_id，不存在返回 None。"""
        return self._sub_sessions.get(sub_agent_name)

    def get_all_sessions(self) -> Dict[str, str]:
        """返回所有 SubAgent session_id 的副本。"""
        return dict(self._sub_sessions)
