"""
AISE ASK - The AISE Learning Program Chatbot
Refactored from monolith into microservices architecture.

Services:
- Auth Service:    User registration, login, and profile management
- Chat Service:    Groq LLM integration and chat history
- Content Service: Content upload, search, and listing
- API Gateway:     Routing, CORS, health checks, and error handling
"""

from gateway.app import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    print("""
    ====================================================
              AISE ASK - Microservices Edition
           Your AI Safety & Engineering Assistant
    ====================================================
    """)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
