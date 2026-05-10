"""
PgvectorMemoryProvider —— 业务实现 ``MemoryProvider`` Protocol。

两张表路由：
- ``MemoryEntry``  事件型 / append-only / vector 召回
- ``MemoryProfile`` 实体型 / upsert / KV 精确召回

写入路由：``CandidateMemory.entity`` 含 ``entity_kind`` + ``entity_key`` → profile
表 UPSERT；否则进 memory_entries。

召回路由：``RecallQuery.metadata`` 中：
- ``entity_filter = {"entity_kind": ..., "entity_key": ...}`` → profile 精确查
- ``include_memory = True``（默认）→ memory_entries 向量召回（需要
  ``embedding_service`` 注入；缺失时退化为按时间倒排）

**Domain 级强绑**：framework 不知道"领域"是什么含义——可能是 project / user /
repo / 等业务定义的隔离边界。本 Provider 构造时绑定 ``domain_id``：所有 write
操作把 ``scope.domain_id`` 强制设为绑定值（覆盖任何外部传入的值），所有 recall
操作也强制按这个 ``domain_id`` 过滤。

业务（FilmGenX）的语义是"一个 domain = 一个 project = 一个剧本"——把 project.id
作为 domain_id 传进来即可；其它业务可以用 user.id / org.id 等。framework 不解释
domain 的具体含义。

每个 domain 应该单独建一个 Provider 实例（业务层启动时按 domain_id 构造）；
多个 domain 并发时 session_factory / embedding_service 可共享。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, func, select, text, update
from sqlalchemy.dialects.postgresql import JSONB, insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.core.agent.memory.embedding import EmbeddingService
from app.core.agent.memory.provider import MemoryProvider
from app.core.agent.memory.types import (
    CandidateMemory,
    RecallQuery,
    RecalledMemory,
)
from app.memory.taxonomy import KIND_REGISTRY, validate_kv
from app.models.memory_entry import MemoryEntry
from app.models.memory_extract_cursor import MemoryExtractCursor
from app.models.memory_profile import MemoryProfile

logger = logging.getLogger(__name__)


class PgvectorMemoryProvider(MemoryProvider):
    """实现 ``MemoryProvider`` Protocol。"""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        domain_id: int | str,
        embedding_service: Optional[EmbeddingService] = None,
        memory_topk: int = 50,
    ) -> None:
        """
        Args:
            session_factory: AsyncSessionFactory 之类，每次操作开新 session
            domain_id: 必填——本 Provider 绑定的"领域"标识。framework 不解释含义；
                FilmGenX 用 ``project.id``（剧本级），其它业务可用 ``user.id`` /
                ``repo.id`` 等。所有 write / recall 强制按这个值锁 ``scope.domain_id``，
                业务忘传 / 传错都不会出现跨域泄露
            embedding_service: 写入时给 content 算向量；召回时给 text_query 算向量。
                None 时 memory_entries 走纯时间倒排，召回质量明显下降但依然能用
            memory_topk: 召回时 memory_entries 最多返回多少条候选（ranker 后续会再过滤）
        """
        if not isinstance(domain_id, (int, str)) or (isinstance(domain_id, str) and not domain_id):
            raise ValueError("domain_id must be a non-empty int or str")
        if isinstance(domain_id, int) and domain_id <= 0:
            raise ValueError("domain_id (int) must be positive")
        self._session_factory = session_factory
        self._domain_id = domain_id
        self._embedding = embedding_service
        self._memory_topk = memory_topk

    def _enforce_domain_scope(self, scope: dict[str, Any]) -> dict[str, Any]:
        """合并外部 scope，但强制 domain_id 用绑定值（防止 leak / cross-write）。"""
        return {**scope, "domain_id": self._domain_id}

    # ---------------------------------------------------------------- #
    # commit_extraction —— 原子写入 + 推进游标
    # ---------------------------------------------------------------- #

    async def commit_extraction(
        self,
        candidates: list[CandidateMemory],
        scope_metadata: dict[str, Any],
        cursor_key: Optional[str] = None,
        cursor_marker: Optional[str] = None,
    ) -> list[str]:
        """单一 PG 事务：所有 candidate 写入 + cursor 推进 atomically。

        Profile candidate（含 entity_kind+entity_key）会按 ``app.memory.taxonomy``
        校验：kind 必须在 ALLOWED_KINDS 内，key 符合 kind 的 open/closed/single 规则，
        value 符合 kind 的 Pydantic schema。**校验失败的 candidate 直接丢弃**（log
        warning），其余正常入库 + cursor 仍然推进。
        """
        if cursor_key is not None and cursor_marker is None:
            raise ValueError("cursor_marker is required when cursor_key is provided")

        scope = self._enforce_domain_scope(scope_metadata)

        # 先按 taxonomy 过滤 profile candidate；保留无 entity 的 entry candidate
        validated_candidates: list[CandidateMemory] = []
        for c in candidates:
            if not _is_profile_candidate(c):
                validated_candidates.append(c)
                continue
            try:
                self._normalize_profile_candidate(c)
            except ValueError as exc:
                logger.warning(
                    "[pgvector] dropping invalid candidate kind=%s key=%s: %s",
                    (c.entity or {}).get("entity_kind"),
                    (c.entity or {}).get("entity_key"),
                    exc,
                )
                continue
            validated_candidates.append(c)
        candidates = validated_candidates

        # 把 embedding 算在事务外（embedding 调用是 RPC 外联，慢，不该卡住 PG 事务）
        memory_candidates = [c for c in candidates if not _is_profile_candidate(c)]
        embeddings_by_idx: dict[int, list[float] | None] = {}
        if memory_candidates and self._embedding is not None:
            try:
                texts = [c.content for c in memory_candidates]
                vecs = await self._embedding.embed(texts)
                for c, v in zip(memory_candidates, vecs):
                    embeddings_by_idx[id(c)] = v
            except Exception:
                logger.exception(
                    "[pgvector] embedding failed; entries will be written without vectors"
                )

        written_ids: list[str] = []

        async with self._session_factory() as session:
            async with session.begin():
                for candidate in candidates:
                    if _is_profile_candidate(candidate):
                        new_id = await self._upsert_profile_in_session(
                            session, candidate, scope
                        )
                    else:
                        emb = embeddings_by_idx.get(id(candidate))
                        new_id = await self._insert_memory_entry_in_session(
                            session, candidate, scope, emb
                        )
                    written_ids.append(new_id)

                if cursor_key is not None:
                    stmt = pg_insert(MemoryExtractCursor).values(
                        cursor_key=cursor_key,
                        marker=cursor_marker,
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["cursor_key"],
                        set_={"marker": cursor_marker},
                    )
                    await session.execute(stmt)
            # session.begin() 退出时整个事务 commit；任一 await 抛错则全部 rollback

        return written_ids

    # ---------------------------------------------------------------- #
    # 事务内的写入辅助（不开 session，不 commit；session 由 caller 管理）
    # ---------------------------------------------------------------- #

    def _normalize_profile_candidate(
        self, candidate: CandidateMemory
    ) -> tuple[str, str, dict[str, Any]]:
        """从 candidate 抽出 (kind, key, value) 并按 taxonomy 校验+归一化。"""
        assert candidate.entity is not None
        entity_kind = candidate.entity.get("entity_kind")
        entity_key = candidate.entity.get("entity_key")
        if not isinstance(entity_kind, str) or not isinstance(entity_key, str):
            raise ValueError("entity_kind / entity_key must both be strings")

        # candidate.entity 里除了 entity_kind / entity_key，剩下的都是 value 字段
        raw_value = {
            k: v
            for k, v in candidate.entity.items()
            if k not in ("entity_kind", "entity_key")
        }
        value = validate_kv(entity_kind, entity_key, raw_value)
        return entity_kind, entity_key, value

    async def _upsert_profile_in_session(
        self,
        session: AsyncSession,
        candidate: CandidateMemory,
        scope_metadata: dict[str, Any],
    ) -> str:
        entity_kind, entity_key, value = self._normalize_profile_candidate(candidate)

        # 把当前生效行 superseded
        stmt = (
            update(MemoryProfile)
            .where(
                and_(
                    MemoryProfile.scope.op("@>")(scope_metadata),
                    MemoryProfile.scope.op("<@")(scope_metadata),  # 双向 @> 实现严格相等
                    MemoryProfile.entity_kind == entity_kind,
                    MemoryProfile.entity_key == entity_key,
                    MemoryProfile.superseded_at.is_(None),
                    MemoryProfile.is_deleted.is_(False),
                )
            )
            .values(superseded_at=datetime.now(timezone.utc))
        )
        await session.execute(stmt)

        row = MemoryProfile(
            scope=dict(scope_metadata),
            entity_kind=entity_kind,
            entity_key=entity_key,
            value=value,
            confidence=float(candidate.confidence),
            extra_metadata=dict(candidate.extraction_metadata),
        )
        session.add(row)
        await session.flush()  # 让 row.id 在不 commit 的情况下可读
        return f"profile:{row.id}"

    async def _insert_memory_entry_in_session(
        self,
        session: AsyncSession,
        candidate: CandidateMemory,
        scope_metadata: dict[str, Any],
        embedding: Optional[list[float]],
    ) -> str:
        row = MemoryEntry(
            scope=dict(scope_metadata),
            kind=candidate.kind,
            content=candidate.content,
            embedding=embedding,
            source=candidate.extraction_metadata.get("source", "agent_output"),
            confidence=float(candidate.confidence),
            extra_metadata=dict(candidate.extraction_metadata),
        )
        session.add(row)
        await session.flush()
        return f"entry:{row.id}"

    # ---------------------------------------------------------------- #
    # 业务扩展：直接 set_kv（绕过 extractor），list_active 全量取
    # ---------------------------------------------------------------- #

    async def set_kv(
        self,
        kind: str,
        key: str,
        value: dict[str, Any],
        *,
        scope_metadata: Optional[dict[str, Any]] = None,
        confidence: float = 1.0,
        extra_metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """**确定性写入**：业务工具 / agent 直接 UPSERT 一条 KV，不走 extractor。

        和 commit_extraction 用同一份 taxonomy 校验逻辑。校验失败抛 ValueError，由
        caller 决定如何处理（一般直接抛回给 LLM 做参数纠正）。
        """
        validated_value = validate_kv(kind, key, value)
        clean_scope = _scope_metadata_for_filter(scope_metadata or {})
        scope = self._enforce_domain_scope(clean_scope)

        async with self._session_factory() as session:
            async with session.begin():
                stmt = (
                    update(MemoryProfile)
                    .where(
                        and_(
                            MemoryProfile.scope.op("@>")(scope),
                            MemoryProfile.scope.op("<@")(scope),
                            MemoryProfile.entity_kind == kind,
                            MemoryProfile.entity_key == key,
                            MemoryProfile.superseded_at.is_(None),
                            MemoryProfile.is_deleted.is_(False),
                        )
                    )
                    .values(superseded_at=datetime.now(timezone.utc))
                )
                await session.execute(stmt)

                row = MemoryProfile(
                    scope=dict(scope),
                    entity_kind=kind,
                    entity_key=key,
                    value=validated_value,
                    confidence=float(confidence),
                    extra_metadata=dict(extra_metadata or {}),
                )
                session.add(row)
                await session.flush()
                new_id = row.id

        return f"profile:{new_id}"

    async def list_active(
        self,
        scope_metadata: Optional[dict[str, Any]] = None,
    ) -> list[RecalledMemory]:
        """全量返回当前 domain 的 active KV。给"全量注入" prompt 用。

        按 (entity_kind, entity_key, created_at) 排序，方便上层按 kind group 后渲染。
        不走 vector 检索，不走 ranker —— KV 是有限集合，全量注入。
        """
        # 过滤出真正的业务 scope 字段（去掉 strategy / query_embedding 这些框架专用 key），
        # 再 enforce domain
        clean_scope = _scope_metadata_for_filter(scope_metadata or {})
        scope = self._enforce_domain_scope(clean_scope)

        async with self._session_factory() as session:
            stmt = (
                select(MemoryProfile)
                .where(
                    MemoryProfile.scope.op("@>")(scope),
                    MemoryProfile.scope.op("<@")(scope),
                    MemoryProfile.superseded_at.is_(None),
                    MemoryProfile.is_deleted.is_(False),
                )
                .order_by(
                    MemoryProfile.entity_kind,
                    MemoryProfile.entity_key,
                    MemoryProfile.created_at,
                )
            )
            rows = (await session.execute(stmt)).scalars().all()

        return [_profile_row_to_recalled(r) for r in rows]

    # ---------------------------------------------------------------- #
    # recall
    # ---------------------------------------------------------------- #

    async def recall(self, query: RecallQuery) -> list[RecalledMemory]:
        # 强制覆盖 domain_id：不允许业务用其他 domain 的 scope 召回
        enriched_metadata = self._enforce_domain_scope(query.metadata)
        scoped_query = query.model_copy(update={"metadata": enriched_metadata})

        # FilmGenX 默认走全量注入（KV 是有限集合，召回 = 全量）。framework 仍然
        # 接收 RecallQuery 走 ranker，但 ranker 在 full_kv 模式下应当是 passthrough。
        strategy = scoped_query.metadata.get("strategy", "full_kv")
        if strategy == "full_kv":
            return await self.list_active(scoped_query.metadata)

        # 旧的 vector_ranked 路径保留：
        results: list[RecalledMemory] = []

        entity_filter = scoped_query.metadata.get("entity_filter") or {}
        if entity_filter:
            results.extend(await self._query_profile(scoped_query, entity_filter))

        # 默认开启 memory_entries 召回；业务可显式关掉
        if scoped_query.metadata.get("include_memory", True):
            results.extend(await self._query_memory_entries(scoped_query))

        return results

    async def _query_profile(
        self,
        query: RecallQuery,
        entity_filter: dict[str, Any],
    ) -> list[RecalledMemory]:
        kind = entity_filter.get("entity_kind")
        key = entity_filter.get("entity_key")
        scope_filter = _scope_metadata_for_filter(query.metadata)

        async with self._session_factory() as session:
            stmt = select(MemoryProfile).where(
                MemoryProfile.scope.op("@>")(scope_filter),
                MemoryProfile.superseded_at.is_(None),
                MemoryProfile.is_deleted.is_(False),
            )
            if kind is not None:
                stmt = stmt.where(MemoryProfile.entity_kind == kind)
            if key is not None:
                stmt = stmt.where(MemoryProfile.entity_key == key)

            rows = (await session.execute(stmt)).scalars().all()

        return [_profile_row_to_recalled(r) for r in rows]

    async def _query_memory_entries(self, query: RecallQuery) -> list[RecalledMemory]:
        scope_filter = _scope_metadata_for_filter(query.metadata)

        # 优先：text_query 走向量召回（embedding 算 query 向量 + 按 cosine 距离 ORDER BY）
        query_vec: Optional[list[float]] = None
        text_query = query.initial_input
        if text_query and self._embedding is not None:
            try:
                vecs = await self._embedding.embed([text_query])
                query_vec = vecs[0] if vecs else None
            except Exception:
                logger.warning(
                    "[pgvector] query embedding failed; falling back to time-desc"
                )

        async with self._session_factory() as session:
            stmt = select(MemoryEntry).where(
                MemoryEntry.scope.op("@>")(scope_filter),
                MemoryEntry.is_deleted.is_(False),
            )
            kinds = query.metadata.get("kinds")
            if kinds:
                stmt = stmt.where(MemoryEntry.kind.in_(kinds))

            if query_vec is not None:
                # cosine 距离：smaller = closer。pgvector 的 <=> 是 cosine distance
                stmt = stmt.where(MemoryEntry.embedding.is_not(None)).order_by(
                    MemoryEntry.embedding.cosine_distance(query_vec)
                )
            else:
                stmt = stmt.order_by(MemoryEntry.created_at.desc())

            stmt = stmt.limit(self._memory_topk)
            rows = (await session.execute(stmt)).scalars().all()

        return [
            RecalledMemory(
                id=f"entry:{r.id}",
                content=r.content,
                kind=r.kind,
                confidence=float(r.confidence),
                created_at=r.created_at,
                embedding=list(r.embedding) if r.embedding is not None else None,
                metadata=dict(r.extra_metadata or {}),
            )
            for r in rows
        ]

    # ---------------------------------------------------------------- #
    # cursor 读 —— 写入路径已经合并到 commit_extraction 的事务里
    # ---------------------------------------------------------------- #

    async def get_extract_cursor(self, cursor_key: str) -> Optional[str]:
        async with self._session_factory() as session:
            stmt = select(MemoryExtractCursor.marker).where(
                MemoryExtractCursor.cursor_key == cursor_key,
                MemoryExtractCursor.is_deleted.is_(False),
            )
            row = await session.execute(stmt)
            value = row.scalar_one_or_none()
        return value


# -------------------------------------------------------------------- #
# helpers
# -------------------------------------------------------------------- #


def _is_profile_candidate(candidate: CandidateMemory) -> bool:
    """业务约定：candidate.entity 含 entity_kind + entity_key → profile。"""
    if not candidate.entity:
        return False
    return "entity_kind" in candidate.entity and "entity_key" in candidate.entity


def _profile_row_to_recalled(row: MemoryProfile) -> RecalledMemory:
    """把 MemoryProfile ORM 行翻译成 framework 的 RecalledMemory。

    value 是 taxonomy 校验过的结构化 dict；这里用 ``content`` 字段拼一个
    简短摘要给框架的 ranker / inject 使用，但 entity 里保留完整 value 字段
    供下游 agent 直接消费。
    """
    value = dict(row.value or {})
    summary = _format_kv_summary(row.entity_kind, row.entity_key, value)
    return RecalledMemory(
        id=f"profile:{row.id}",
        content=summary,
        kind=row.entity_kind,
        entity={
            "entity_kind": row.entity_kind,
            "entity_key": row.entity_key,
            **value,
        },
        confidence=float(row.confidence),
        created_at=row.created_at,
        metadata=dict(row.extra_metadata or {}),
    )


def _format_kv_summary(kind: str, key: str, value: dict[str, Any]) -> str:
    """把结构化 value 渲染成给 LLM 看的紧凑摘要。

    每个 kind 自己挑代表字段（character.appearance / scene.atmosphere / preference.description...）。
    上层 inject 时还会再 group 渲染，这里给个单行 fallback。
    """
    parts: list[str] = []
    for field in ("description", "summary", "appearance", "atmosphere", "name"):
        v = value.get(field)
        if isinstance(v, str) and v:
            parts.append(v)
            break
    if not parts:
        # 兜底：拼字段
        parts.append(", ".join(f"{k}={v}" for k, v in value.items() if v))
    return f"[{kind}.{key}] " + (parts[0] if parts else "")


def _scope_metadata_for_filter(metadata: dict[str, Any]) -> dict[str, Any]:
    """从 RecallQuery.metadata 抽出真正的 scope 字段，过滤掉框架专用 key。

    框架 / 业务 key 共用一个 metadata bag，召回时只把"业务 scope"传给 JSONB 查询；
    ``query_embedding`` / ``entity_filter`` / ``include_memory`` / ``kinds`` 等是
    召回参数，不参与 scope 比对。
    """
    reserved = {"query_embedding", "entity_filter", "include_memory", "kinds", "strategy"}
    return {k: v for k, v in metadata.items() if k not in reserved}
