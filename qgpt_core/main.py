"""FastAPI app creation, logger configuration and main API routes."""

from qgpt_core.di import global_injector
from qgpt_core.launcher import create_app

app = create_app(global_injector)
