from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
# from .config import GoogleDriveConfig
from everi_ai_qgpt_core.components.gdrive.client import GoogleDriveClient
import json
from everi_ai_qgpt_core.server.utils.auth import authenticated
import logging
from pydantic import BaseModel, Field
from typing import Literal
import json

from everi_ai_qgpt_core.server.ingest.ingest_service import IngestService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
gdrive_router = APIRouter(prefix="/v1", dependencies=[Depends(authenticated)])

drive_client = GoogleDriveClient()

# class IngestTextBody(BaseModel):
#     file_name: str = Field(examples=["Avatar: The Last Airbender"])
#     text: str = Field(
#         examples=[
#             "Avatar is set in an Asian and Arctic-inspired world in which some "
#             "people can telekinetically manipulate one of the four elements—water, "
#             "earth, fire or air—through practices known as 'bending', inspired by "
#             "Chinese martial arts."
#         ]
#     )

# class IngestResponse(BaseModel):
#     object: Literal["list"]
#     model: Literal["private-gpt"]
#     data: list[IngestedDoc]

@gdrive_router.get("/drive/files", summary="List files from Google Drive")
async def list_drive_files(limit: int = 5):
    try:
        logger.info("Listing files from Google Drive")
        # Fetch Google Docs only
        files = drive_client.list_files(limit, mime_type="application/vnd.google-apps.document")
        logger.info(f"Found {len(files)} Google Docs")

        content = []
        for file in files:
            try:
                data = drive_client.read_google_doc(file["id"])
                content.append({
                    "id": file["id"],
                    "name": file["name"],
                    "content": data
                })
            except HttpError as e:
                if e.resp.status == 403 and "fileNotDownloadable" in str(e):
                    logger.warning(f"Skipping file {file['id']} ({file['name']}): Not downloadable")
                    continue
                logger.error(f"Failed to read file {file['id']}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error reading file {file['id']}: {str(e)}")
                continue

        if not content:
            return {"message": "No readable Google Docs found", "files": []}

        return {"files": content}

    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@gdrive_router.get("/drive/injestfiles", summary="List files from Google Drive")
async def injest_files_from_drive(request: Request):
    try:
        file_ids = []
        files = drive_client.load_files()
        # logger.info(f"Files : {files}")
        filesarray = files["files"]
        logger.info(f"Files array : {filesarray}")
        for file in filesarray:
            try:
                logger.info("File: %s", file)
                service = request.state.injector.get(IngestService)
                
                # Clean BOM from content
                content = file["content"].lstrip('\ufeff')
                logger.info("Cleaned content (first 100 chars): %s", content[:100])
                ingested_documents = service.ingest_text(file["name"], content)
                logger.info(ingested_documents)
                file_ids.append(file["id"])
            except Exception as e:
                logger.error(f"Failed to read file {file['id']}: {str(e)}")
                continue
        # return IngestResponse(object="list", model="private-gpt", data=ingested_documents)
        return file_ids

    except Exception as e:
        logger.error(f"Error during data insertion: {str(e)}")
        raise
