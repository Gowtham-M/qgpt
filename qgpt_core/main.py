"""FastAPI app creation, logger configuration and main API routes."""

# Fix for OpenMP runtime conflict - must be set before importing any libraries that use OpenMP
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from qgpt_core.di import global_injector
from qgpt_core.launcher import create_app

app = create_app(global_injector)

# --- CORS Middleware for local frontend development ---
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------------------------------------------
