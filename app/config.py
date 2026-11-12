from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # Signs the session cookie. Anyone who knows it can forge a login.
    secret_key: str


settings = Settings()
