"""Central configuration — everything comes from the .env file."""
import os

from dotenv import load_dotenv

load_dotenv()

# Groq LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# SAP connection
SAP_BASE_URL = os.getenv("SAP_BASE_URL", "").rstrip("/")   # e.g. https://myhost:44300
SAP_USER = os.getenv("SAP_USER", "")
SAP_PASSWORD = os.getenv("SAP_PASSWORD", "")
SAP_CLIENT = os.getenv("SAP_CLIENT", "")                   # e.g. 100 (optional)
SAP_VERIFY_SSL = os.getenv("SAP_VERIFY_SSL", "true").lower() != "false"


def validate() -> list[str]:
    """Return a list of missing configuration values (empty = all good)."""
    missing = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not SAP_BASE_URL:
        missing.append("SAP_BASE_URL")
    if not SAP_USER:
        missing.append("SAP_USER")
    if not SAP_PASSWORD:
        missing.append("SAP_PASSWORD")
    return missing
