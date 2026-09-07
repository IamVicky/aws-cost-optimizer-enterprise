"""Centralized configuration. Values come from environment variables / .env,
never hardcoded paths or secrets committed to the repo."""
import os
from dotenv import load_dotenv

load_dotenv()

PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))

DATA_RAW_DIR = os.getenv("DATA_RAW_DIR", os.path.join(PACKAGE_ROOT, "..", "..", "data", "raw"))
DATA_PROCESSED_DIR = os.getenv("DATA_PROCESSED_DIR", os.path.join(PACKAGE_ROOT, "..", "..", "data", "processed"))
DUCKDB_PATH = os.getenv("DUCKDB_PATH", os.path.join(DATA_PROCESSED_DIR, "cloudintel.duckdb"))

ACCOUNTS_CONFIG_PATH = os.getenv("ACCOUNTS_CONFIG_PATH", os.path.join(PACKAGE_ROOT, "..", "..", "config", "accounts.json"))
SERVICES_CONFIG_DIR = os.getenv("SERVICES_CONFIG_DIR", os.path.join(PACKAGE_ROOT, "..", "..", "config", "services"))

AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama-3.3-70b-versatile")
