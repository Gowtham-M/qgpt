from pathlib import Path

from everi_ai_qgpt_core.constants import PROJECT_ROOT_PATH
from everi_ai_qgpt_core.settings.settings import settings


def _absolute_or_from_project_root(path: str) -> Path:
    if path.startswith("/"):
        return Path(path)
    return PROJECT_ROOT_PATH / path


models_path: Path = PROJECT_ROOT_PATH / "models"
models_cache_path: Path = models_path / "cache"
docs_path: Path = PROJECT_ROOT_PATH / "docs"
everi_ai_qgpt_vectordb_qdrant_path: Path = _absolute_or_from_project_root(
    settings().data.everi_ai_qgpt_vectordb_qdrant_folder
)
