from pathlib import Path

from app.core.config import Settings


def test_settings_env_file_points_to_backend_dotenv():
    env_file = Path(Settings.model_config["env_file"])

    assert env_file.is_absolute()
    assert env_file.name == ".env"
    assert env_file.parent.name == "backend"
