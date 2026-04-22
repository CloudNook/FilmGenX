from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


VERSIONS_DIR = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "db"
    / "migrations"
    / "versions"
)


def load_migration_module(filename: str):
    module_path = VERSIONS_DIR / filename
    spec = spec_from_file_location(filename.replace(".py", ""), module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_supervisor_workflows_migration_includes_base_columns(monkeypatch):
    migration = load_migration_module(
        "t3u4v5w6x7y8_create_supervisor_workflows_table.py"
    )
    captured: dict[str, list[str]] = {}

    def fake_create_table(name, *columns, **kwargs):
        captured["table_name"] = name
        captured["columns"] = [
            column.name for column in columns if getattr(column, "name", None)
        ]

    monkeypatch.setattr(migration.op, "create_table", fake_create_table)

    migration.upgrade()

    assert captured["table_name"] == "supervisor_workflows"
    assert {
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
    }.issubset(set(captured["columns"]))


def test_add_supervisor_workflow_base_columns_migration_backfills_missing_columns(
    monkeypatch,
):
    migration = load_migration_module(
        "v5w6x7y8z9a_add_supervisor_workflow_base_columns.py"
    )
    added_columns: list[str] = []
    created_indexes: list[str] = []

    class FakeBatchOp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def add_column(self, column):
            added_columns.append(column.name)

    class FakeInspector:
        def get_columns(self, table_name):
            assert table_name == "supervisor_workflows"
            return [{"name": "id"}]

        def get_indexes(self, table_name):
            assert table_name == "supervisor_workflows"
            return []

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.sa, "inspect", lambda bind: FakeInspector())
    monkeypatch.setattr(
        migration.op,
        "batch_alter_table",
        lambda table_name: FakeBatchOp(),
    )
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda name, table_name, columns, unique=False: created_indexes.append(name),
    )

    migration.upgrade()

    assert added_columns == [
        "created_at",
        "updated_at",
        "is_deleted",
        "deleted_at",
    ]
    assert created_indexes == ["ix_supervisor_workflows_is_deleted"]


def test_drop_agent_interrupt_state_migration_removes_legacy_table(monkeypatch):
    migration = load_migration_module(
        "w6x7y8z9a0b_drop_agent_interrupt_state_table.py"
    )
    dropped_tables: list[str] = []

    class FakeInspector:
        def get_table_names(self):
            return ["agent_interrupt_state", "supervisor_workflows"]

    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    monkeypatch.setattr(migration.sa, "inspect", lambda bind: FakeInspector())
    monkeypatch.setattr(
        migration.op,
        "drop_table",
        lambda table_name: dropped_tables.append(table_name),
    )

    migration.upgrade()

    assert dropped_tables == ["agent_interrupt_state"]


def test_normalize_supervisor_workflow_state_migration_creates_structured_tables(
    monkeypatch,
):
    migration = load_migration_module(
        "y2z3a4b5c6d7_normalize_supervisor_workflow_state.py"
    )
    created_tables: list[str] = []
    dropped_columns: list[str] = []

    class FakeBatchOp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def drop_column(self, column_name):
            dropped_columns.append(column_name)

    monkeypatch.setattr(
        migration.op,
        "create_table",
        lambda name, *columns, **kwargs: created_tables.append(name),
    )
    monkeypatch.setattr(migration.op, "f", lambda name: name)
    monkeypatch.setattr(migration.op, "create_index", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        migration.op,
        "batch_alter_table",
        lambda table_name: FakeBatchOp(),
    )

    migration.upgrade()

    assert created_tables == [
        "supervisor_workflow_nodes",
        "supervisor_workflow_node_dependencies",
    ]
    assert dropped_columns == ["workflow_snapshot"]
