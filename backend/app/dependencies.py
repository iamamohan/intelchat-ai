from app.config import Settings, settings

def get_settings() -> Settings:
    """Dependency provider for the application settings."""
    return settings
