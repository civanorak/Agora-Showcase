from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sqlite_path: str = "agora.db"
    database_url: str = "postgresql://agora:agora@localhost:5432/agora"
    api_key_hash_salt: str = "change-me-in-production"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    log_level: str = "INFO"
    # Set AGORA_DEMO_MODE=1 to enable demo-key bypass and demo signatures.
    # Must never be set in production. demo.bat sets this automatically.
    demo_mode: bool = False
    admin_token: str = ""  # set AGORA_ADMIN_TOKEN; empty = /sites endpoints disabled

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "env_prefix": "AGORA_"}


_DEFAULT_SALT = "change-me-in-production"


def verify_production_secrets(s: "Settings") -> None:
    """Fail fast on a public host started with insecure defaults.

    Only enforced when demo mode is OFF — the demo intentionally runs open. In
    production the IP-hash salt must be changed (D006) and an admin token must be
    set, otherwise privacy/auth guarantees silently degrade.
    """
    if s.demo_mode:
        return
    problems: list[str] = []
    if s.api_key_hash_salt == _DEFAULT_SALT or len(s.api_key_hash_salt) < 16:
        problems.append("AGORA_API_KEY_HASH_SALT must be a long, non-default random value")
    if not s.admin_token or len(s.admin_token) < 16:
        problems.append("AGORA_ADMIN_TOKEN must be set to a long random value")
    if problems:
        raise RuntimeError(
            "Refusing to start with insecure production config: " + "; ".join(problems)
        )


settings = Settings()
