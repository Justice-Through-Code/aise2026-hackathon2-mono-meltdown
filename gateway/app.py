"""
API Gateway - Central entry point for the AISE ASK application.

Responsibilities:
- CORS configuration
- Mounting service routers
- Health check, status, and utility endpoints
- Centralized error handling
- Database initialization on startup
"""

import random
import time

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.auth.router import router as auth_router
from services.chat.router import router as chat_router
from services.content.router import router as content_router
from services.shared.auth import verify_token
from services.shared.config import APP_VERSION, CORS_ORIGINS, DEBUG_MODE
from services.shared.database import get_connection, init_db, seed_default_content

app = FastAPI(
    title="AISE ASK",
    description="The AISE Learning Program Chatbot - Ask me anything about the program!",
    version=APP_VERSION,
)

# CORS - configured from environment, no wildcard "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount service routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(content_router)

# Track startup time for uptime calculation
_system_start_time = time.time()


@app.on_event("startup")
async def startup_event():
    """Initialize database and seed default content on startup."""
    init_db()
    seed_default_content()


# ============================================================
# Gateway endpoints - Health, status, info, and utilities
# ============================================================

@app.get("/")
async def root():
    """Root endpoint with API overview."""
    return {
        "app": "AISE ASK",
        "tagline": "Your AI Safety & Engineering Program Assistant",
        "version": APP_VERSION,
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_status = "unknown"
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        db_status = "connected"
        conn.close()
    except Exception:
        db_status = "error"

    uptime = time.time() - _system_start_time

    return {
        "status": "ok",
        "database": db_status,
        "uptime_seconds": round(uptime, 2),
        "version": APP_VERSION,
        "debug_mode": DEBUG_MODE,
    }


@app.get("/status")
async def detailed_status(user: dict = Depends(verify_token)):
    """Detailed system status (requires authentication)."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    user_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM chat_history")
    chat_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM content")
    content_count = c.fetchone()[0]
    conn.close()

    return {
        "system": {
            "uptime_seconds": round(time.time() - _system_start_time, 2),
            "debug_mode": DEBUG_MODE,
            "version": APP_VERSION,
        },
        "database": {
            "users": user_count,
            "chat_messages": chat_count,
            "content_items": content_count,
        },
    }


@app.get("/api-info")
async def api_info():
    """API documentation listing all available endpoints."""
    return {
        "endpoints": {
            "POST /register": "Register a new user",
            "POST /login": "Login and get JWT token",
            "POST /chat": "Send a message to AISE ASK (requires auth)",
            "GET /chat/history": "Get your chat history (requires auth)",
            "POST /content/upload": "Upload lesson content (requires auth)",
            "POST /content/upload-file": "Upload content from JSON file (requires auth)",
            "POST /content/search": "Search content (requires auth)",
            "GET /content": "List all content (requires auth)",
            "GET /me": "Get your profile (requires auth)",
            "GET /health": "Health check",
            "GET /status": "Detailed status (requires auth)",
            "GET /analytics": "Usage analytics (requires auth)",
            "GET /dad-joke": "Get a programming dad joke",
        },
        "auth": "Bearer token via Authorization header. Get a token from /register or /login.",
    }


@app.get("/analytics")
async def analytics(user: dict = Depends(verify_token)):
    """Usage analytics for the platform."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT user_id) FROM chat_history")
    active_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM chat_history")
    total_messages = c.fetchone()[0]
    c.execute("SELECT SUM(tokens_used) FROM chat_history")
    total_tokens = c.fetchone()[0] or 0
    conn.close()

    return {
        "active_chatters": active_users,
        "total_messages": total_messages,
        "total_tokens_consumed": total_tokens,
        "estimated_cost": round(total_tokens * 0.0000001, 4),
    }


DAD_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "A SQL query walks into a bar, walks up to two tables and asks... 'Can I JOIN you?'",
    "Why do Java developers wear glasses? Because they don't C#.",
    "How many programmers does it take to change a light bulb? None, that's a hardware problem.",
    "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
    "What's a programmer's favorite hangout place? Foo Bar.",
    "Why did the developer go broke? Because he used up all his cache.",
    "What do you call a snake that's exactly 3.14 meters long? A pi-thon.",
    "Why did the functions stop calling each other? Because they got too many arguments.",
    "There are only 10 kinds of people in the world: those who understand binary and those who don't.",
    "Why do microservices never get lonely? Because they're always in a cluster.",
    "What's a monolith's favorite song? 'All By Myself'.",
    "Why did the REST API break up with SOAP? Too much baggage.",
]


@app.get("/dad-joke")
async def dad_joke():
    """Get a programming dad joke. No auth required - some things are sacred."""
    return {
        "joke": random.choice(DAD_JOKES),
        "groaned": True,
        "dad_approved": True,
    }


# ============================================================
# Error handlers
# ============================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "This endpoint doesn't exist. Check /api-info for available endpoints.",
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Custom 500 handler."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "Something went wrong. Please try again later.",
            "debug_hint": str(exc) if DEBUG_MODE == "chaos" else "Enable DEBUG_MODE=chaos for details",
        },
    )
