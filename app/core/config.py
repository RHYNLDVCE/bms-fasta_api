from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int
    TRANSACTION_SERVICE_URL: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Pylance will complain, but this works at runtime
settings = Settings()  # type: ignore
