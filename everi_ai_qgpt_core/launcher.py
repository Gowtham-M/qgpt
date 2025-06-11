# """FastAPI app creation, logger configuration and main API routes."""

import logging
from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # Update by abdur
from injector import Injector
from llama_index.core.callbacks import CallbackManager
from llama_index.core.callbacks.global_handlers import create_global_handler
from llama_index.core.settings import Settings as LlamaIndexSettings
from pathlib import Path  # Update by kali
from fastapi.middleware.cors import CORSMiddleware

# Import API routers
from everi_ai_qgpt_core.server.chat.chat_router import chat_router
from everi_ai_qgpt_core.server.chunks.chunks_router import chunks_router
from everi_ai_qgpt_core.server.completions.completions_router import completions_router
from everi_ai_qgpt_core.server.embeddings.embeddings_router import embeddings_router
from everi_ai_qgpt_core.server.health.health_router import health_router
from everi_ai_qgpt_core.server.ingest.ingest_router import ingest_router
from everi_ai_qgpt_core.server.recipes.summarize.summarize_router import summarize_router
from everi_ai_qgpt_core.server.config.config_router import config_router
from everi_ai_qgpt_core.server.gdrive.gdrive_router import gdrive_router
from everi_ai_qgpt_core.server.onedrive.onedrive_router import onedrive_router
from everi_ai_qgpt_core.server.images.images_router import images_router
from everi_ai_qgpt_core.settings.settings import Settings


logger = logging.getLogger(__name__)

def create_app(root_injector: Injector) -> FastAPI:
    """Creates and configures the FastAPI app for integration with React.js."""

    async def bind_injector_to_request(request: Request) -> None:
        """Attach the dependency injector to each request."""
        request.state.injector = root_injector

    # Initialize FastAPI app
    app = FastAPI(dependencies=[Depends(bind_injector_to_request)])

    app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    # Register API routers
    app.include_router(completions_router)
    app.include_router(chat_router)
    app.include_router(chunks_router)
    app.include_router(ingest_router)
    app.include_router(summarize_router)
    app.include_router(embeddings_router)
    app.include_router(health_router)
    app.include_router(config_router)
    app.include_router(gdrive_router)
    app.include_router(onedrive_router)
    app.include_router(images_router)

    # Enable LlamaIndex Observability
    global_handler = create_global_handler("simple")
    if global_handler:
        LlamaIndexSettings.callback_manager = CallbackManager([global_handler])

    # Updated by kali
    BASE_DIR = Path(__file__).resolve().parent
    FRONTEND_BUILD_PATH = (BASE_DIR / ".." / "everi_ai_qgpt_ui" / "build").resolve()

    # Ensure the directory exists
    if not FRONTEND_BUILD_PATH.exists():
        raise RuntimeError(f"Directory '{FRONTEND_BUILD_PATH}' does not exist")

    # Serve static files (React frontend)
    app.mount("/static", StaticFiles(directory=str(FRONTEND_BUILD_PATH / "static")), name="static")

    ######################
    # Mount React frontend
    # app.mount("/", StaticFiles(directory="C:\\Everi\\Application\\EveriQGPT-React-new\\QGPT-React\\everi_ai_qgpt_ui\\build", html=True), name="react-app")

    # app.mount("/", StaticFiles(directory="C:\\Users\\abdur.mohammed\\Downloads\\private-gpt-kali\\private-gpt\\everi_ai_qgpt_ui\\build", html=True), name="react-app")

    # Update by abdur
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        return FileResponse(str(FRONTEND_BUILD_PATH / "index.html"))

    logger.info("React frontend successfully mounted.")
    return app
