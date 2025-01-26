import uvicorn
from config import settings
import logging
import sys
from pathlib import Path
from init_db import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'DB_HOST', 'DB_PORT', 'DB_USER', 
        'DB_PASSWORD', 'DB_NAME', 'SECRET_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not getattr(settings, var, None)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    return True

def create_required_directories():
    """Create required directories if they don't exist"""
    log_dir = Path("logs")
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
        logger.info("Created logs directory")
    return True

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,
    )

    # Add OPTIONS handler for all routes
    @app.options("/{path:path}")
    async def options_handler():
        return {}

    # Import the router and mount it at API prefix
    from main import router
    app.include_router(router, prefix=settings.API_V1_PREFIX)

    return app

def main():
    """Main application entry point"""
    try:
        logger.info("Starting application initialization...")
        check_environment()
        create_required_directories()
        init_db()
        
        logger.info("Creating FastAPI application...")
        app = create_app()
        
        logger.info(f"Starting server on http://0.0.0.0:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 