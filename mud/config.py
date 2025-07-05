import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mud.db")

# Configuration for servers
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))

# Comma separated list of allowed CORS origins
CORS_ORIGINS = [
    origin.strip() for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
]
