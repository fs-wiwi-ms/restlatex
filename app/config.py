from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RESTLATEX_", case_sensitive=False)

    TIMEOUT_SECONDS: int = 30
    MAX_MEMORY_MB: int = 512
    MAX_FILE_SIZE_MB: int = 50

    BWRAP_PATH: str = "/usr/bin/bwrap"
    LATEXMK_PATH: str = "/usr/bin/latexmk"

    TEMP_DIR: str = "/tmp"
    JOB_PREFIX: str = "compile_"
    APP_DIR: str = "/app"

    CANDIDATE_RO_BINDS: List[str] = [
        "/usr",
        "/lib",
        "/lib64",
        "/bin",
        "/etc/texmf",
        "/var/lib/texmf",
        "/usr/share/texlive",
        "/usr/share/texmf",
        "/etc/alternatives",
        "/etc/ld.so.cache",
        "/etc/ld.so.conf",
        "/etc/ld.so.conf.d",
        "/etc/fonts",
    ]


settings = Settings()
