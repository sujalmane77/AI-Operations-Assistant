"""Application configuration settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY_IMPL", "none")

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Config:
    """Runtime configuration for the project."""

    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
    dry_run: bool = True
    sqlite_db: str = "data/assistant.db"
    chroma_db: str = "data/chroma"
    documents_dir: str = "data/documents"
    chroma_collection: str = "company_handbook"
    embedding_model: str = "all-MiniLM-L6-v2"
    primary_model: str = "openai/gpt-oss-120b"
    fallback_model: str = "gemini-flash-latest"
    google_credentials_path: str = "credentials.json"
    google_token_path: str = "token.json"
    agent_max_steps: int = 6

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            groq_api_key=_get("GROQ_API_KEY"),
            gemini_api_key=_get("GEMINI_API_KEY"),
            google_client_id=_get("GOOGLE_CLIENT_ID"),
            google_client_secret=_get("GOOGLE_CLIENT_SECRET"),
            dry_run=(_get("DRY_RUN", "true").lower() == "true"),
            sqlite_db=_get("SQLITE_DB", "data/assistant.db"),
            chroma_db=_get("CHROMA_DB", "data/chroma"),
            documents_dir=_get("DOCUMENTS_DIR", "data/documents"),
            chroma_collection=_get("CHROMA_COLLECTION", "company_handbook"),
            embedding_model=_get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            primary_model=_get("PRIMARY_MODEL", "openai/gpt-oss-120b"),
            fallback_model=_get("FALLBACK_MODEL", "gemini-flash-latest"),
            google_credentials_path=_get("GOOGLE_CREDENTIALS_PATH", "credentials.json"),
            google_token_path=_get("GOOGLE_TOKEN_PATH", "token.json"),
            agent_max_steps=int(_get("AGENT_MAX_STEPS", "6")),
        )

    def require_runtime(self, *names: str) -> None:
        missing = [name for name in names if not getattr(self, name, None)]
        if missing:
            raise RuntimeError(
                "Missing required configuration values: "
                + ", ".join(missing)
                + ". Add them to your .env file."
            )


config = Config.from_env()
