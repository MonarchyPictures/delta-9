from app.main import app

if __name__ == "__main__":
    import uvicorn
    # Binds to 0.0.0.0 to fix host resolution issues
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # NOT 127.0.0.1
        port=8000,
        reload=True
    )
