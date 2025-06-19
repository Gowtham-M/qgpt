"""FastAPI app creation, logger configuration and main API routes."""

# Fix for OpenMP runtime conflict - must be set before importing any libraries that use OpenMP
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from everi_ai_qgpt_core.di import global_injector
from everi_ai_qgpt_core.launcher import create_app

app = create_app(global_injector)
