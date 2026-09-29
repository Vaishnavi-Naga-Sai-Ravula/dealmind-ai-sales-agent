from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')

    database_path: Path = ROOT / 'data' / 'dealmind.db'
    seed_sample_data: bool = True
    frontend_origin: str = 'http://localhost:5173'
    hindsight_base_url: str = ''
    hindsight_api_key: str = ''
    hindsight_bank_prefix: str = Field(default='dealmind', pattern=r'^[a-zA-Z0-9_-]+$')
    hindsight_timeout: float = Field(default=60, gt=0, le=300)
    intelligence_mode: Literal['hindsight', 'demo'] = 'hindsight'
