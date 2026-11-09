import os


def obter_environment() -> str:
    env = os.getenv("ENVIRONMENT", "").strip().lower()
    if env:
        return env
    if os.getenv("RENDER", "").strip().lower() == "true":
        return "production"
    return ""
