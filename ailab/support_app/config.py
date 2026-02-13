import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.tiktoken_cache_dir = os.getenv("TIKTOKEN_CACHE_DIR", "")

        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_embeddings_model = os.getenv(
            "OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-large"
        )
        self.openai_verify_ssl = os.getenv("OPENAI_VERIFY_SSL", "false").lower() in (
            "1",
            "true",
            "yes",
            "y",
        )

        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_KEY", "")
        self.supabase_verify_ssl = os.getenv("SUPABASE_VERIFY_SSL", "true").lower() in (
            "1",
            "true",
            "yes",
            "y",
        )

        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.82"))

    def validate(self) -> None:
        missing: list[str] = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_key:
            missing.append("SUPABASE_KEY")
        if missing:
            raise RuntimeError("Missing environment variables: " + ", ".join(missing))


settings = Settings()

if settings.tiktoken_cache_dir:
    os.environ["TIKTOKEN_CACHE_DIR"] = settings.tiktoken_cache_dir
