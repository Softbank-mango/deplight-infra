# FastAPI Deploy Test

Simple FastAPI application for testing Deplight Platform deployment.

## Features

- Fast and lightweight API
- Health check endpoints
- Status monitoring
- Zero-configuration deployment

## Endpoints

- `GET /` - Root endpoint with welcome message
- `GET /health` - Health check
- `GET /api/status` - API status and available endpoints
- `GET /api/info` - Application information

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

The application will be available at `http://localhost:8000`

## Deployment

This repository is designed to be deployed automatically through the Deplight Platform. Simply push this repository to trigger the deployment workflow.

## Tech Stack

- FastAPI 0.104.1
- Uvicorn (ASGI server)
- Python 3.11+
