import os

# Configuration for servers
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# Comma separated list of allowed CORS origins
CORS_ORIGINS = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "*").split(",")]
