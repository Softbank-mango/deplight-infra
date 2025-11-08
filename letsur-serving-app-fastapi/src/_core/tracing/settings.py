from pydantic_settings import BaseSettings


class LangfuseSettings(BaseSettings):
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_HOST: str
