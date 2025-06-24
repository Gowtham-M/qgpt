"""Maps services initialization module."""

import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Export the maps router
from qgpt_core.server.maps.maps_router import maps_router
