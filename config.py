from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str

    # AI
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    groq_qa_model: str = "llama-3.1-8b-instant"

    # Email
    resend_api_key: str
    from_email: str
    from_name: str = "mofa-letter"

    # Application
    app_base_url: str
    admin_api_key: str
    scheduler_api_key: str
    env: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
