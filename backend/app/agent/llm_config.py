from app.config.settings import settings


_runtime_config: dict[str, str] = {}


def _usable(value: str | None) -> bool:
    return bool(value and not value.lower().startswith("sk-your-"))


def get_config() -> dict[str, str]:
    if _runtime_config:
        return dict(_runtime_config)
    if _usable(settings.OPENAI_API_KEY):
        return {"api_key": settings.OPENAI_API_KEY, "base_url": settings.OPENAI_BASE_URL, "model": settings.OPENAI_MODEL}
    if _usable(settings.QWEN_API_KEY):
        return {"api_key": settings.QWEN_API_KEY, "base_url": settings.QWEN_BASE_URL, "model": settings.QWEN_MODEL}
    return {"api_key": "", "base_url": settings.OPENAI_BASE_URL, "model": settings.OPENAI_MODEL}


def set_config(api_key: str, base_url: str, model: str) -> None:
    _runtime_config.update({"api_key": api_key, "base_url": base_url.rstrip("/"), "model": model})
