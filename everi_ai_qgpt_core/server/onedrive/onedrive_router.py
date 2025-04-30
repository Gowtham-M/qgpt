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
    # token = onedrive.authenticate()
    token = onedrive.initialize()
    files = onedrive.list_and_preview_files(token)
    file_ids = []
    for item in files:
        item_name = item.get('name')
        item_id = item.get('id')
        is_folder = 'folder' in item  # Recursively list contents of this folder
        print(f"\n🔹 File: {item_name} (ID: {item_id})")
        try:
            file_content = onedrive.download_file(token['access_token'], item_id)
            preview = onedrive.preview_file(file_content, item_name)
            service = request.state.injector.get(IngestService)
            ingested_documents = service.ingest_text(item_name, file_content)
            file_ids.append(item_id)
            print(f"📄 Preview:\n{preview}\n")
        except Exception as e:
            print(f"❌ Could not preview file {item_name}: {e}")

    return "DOne"
 