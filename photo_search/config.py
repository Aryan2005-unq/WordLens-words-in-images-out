"""Application configuration loaded from the environment."""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "photo_search")
    db_user: str = os.getenv("DB_USER", "photo_search")
    db_password: str = os.getenv("DB_PASSWORD", "")
    model_id: str = os.getenv("CLIP_MODEL_ID", "openai/clip-vit-base-patch32")
    image_dir: Path = Path(os.getenv("IMAGE_DIR", "data/images")).resolve()
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    embedding_dimension: int = 512


settings = Settings()
