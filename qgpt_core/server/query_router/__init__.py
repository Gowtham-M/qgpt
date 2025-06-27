"""Query routing services initialization module."""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Export the query router
from qgpt_core.server.query_router.query_router import query_router
