"""FastAPI app creation, logger configuration and main API routes."""

from everi_ai_qgpt_core.di import global_injector
from everi_ai_qgpt_core.launcher import create_app

app = create_app(global_injector)
