from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from everi_ai_qgpt_core.server.ingest.ingest_service import IngestService
from everi_ai_qgpt_core.server.ingest.model import IngestedDoc
from everi_ai_qgpt_core.server.utils.auth import authenticated


from everi_ai_qgpt_core.server.onedrive.onedrive_client import OneDriveClient
import logging

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

onedrive = OneDriveClient()


onedrive_router = APIRouter(prefix="/v1", dependencies=[Depends(authenticated)])

@onedrive_router.get("/onedrive/injestfiles", summary="List files from Google Drive")
async def injest_files_from_one_drive(request: Request):
    # onedrive.authenticate()
    files = onedrive.list_files()
    for file in files:
        logger.info("%s",file)
        pass
    return "DOne"
 