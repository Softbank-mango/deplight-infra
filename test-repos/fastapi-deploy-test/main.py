from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="FastAPI Deploy Test",
    description="Simple FastAPI application for testing Deplight deployment",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Hello from FastAPI Deploy Test!",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "deployed_with": "Deplight Platform"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "fastapi-deploy-test"
    }

@app.get("/api/status")
async def status():
    """API status endpoint"""
    return {
        "api": "online",
        "endpoints": ["/", "/health", "/api/status", "/api/info"],
        "features": ["fast-deployment", "ai-powered", "zero-config"]
    }

@app.get("/api/info")
async def info():
    """Application information endpoint"""
    return {
        "name": "FastAPI Deploy Test",
        "framework": "FastAPI",
        "language": "Python",
        "deployment_platform": "Deplight"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
