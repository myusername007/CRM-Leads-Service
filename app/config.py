from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://crm:crm_secret@localhost:5432/crm_leads"
    ANTHROPIC_API_KEY: str 
    
    class Config:
        env_file = ".env"


settings = Settings()
