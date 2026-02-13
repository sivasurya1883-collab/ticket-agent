import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_SSL_VERIFY = os.getenv("SUPABASE_SSL_VERIFY", "true").strip().lower() not in {"0", "false", "no"}

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "720"))

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://genailab.tcs.in")
LLM_MODEL = os.getenv("LLM_MODEL", "azure/genailab-maas-gpt-4o-mini")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").strip().lower() not in {"0", "false", "no"}
LLM_SSL_VERIFY = os.getenv("LLM_SSL_VERIFY", "true").strip().lower() not in {"0", "false", "no"}
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
