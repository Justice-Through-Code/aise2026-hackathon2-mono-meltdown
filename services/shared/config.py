"""
Shared configuration for all AISE ASK microservices.
All secrets and settings are loaded from environment variables.
"""

import os

# Security - loaded from environment, never hardcoded
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
TOKEN_EXPIRY_SECONDS = int(os.getenv("TOKEN_EXPIRY_SECONDS", "86400"))

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", "aise_ask.db")

# Groq LLM API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Application settings
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000"
    ).split(",")
]
MAX_CHAT_HISTORY = int(os.getenv("MAX_CHAT_HISTORY", "10"))
DEBUG_MODE = os.getenv("DEBUG_MODE", "off")

# App metadata
APP_VERSION = "1.0.0"
