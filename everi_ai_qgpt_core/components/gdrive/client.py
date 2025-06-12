from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
import google
from fastapi import HTTPException
from googleapiclient.errors import HttpError
import json
import os
import io
import tempfile
import logging
from pathlib import Path
from typing import List, Tuple
from fastapi import Request
from pydantic import BaseModel, Field
from typing import Literal

# Configure logging
from .config import GoogleDriveConfig
from llama_index.core.schema import Document
from everi_ai_qgpt_core.components.ingest.ingest_helper import IngestionHelper
from everi_ai_qgpt_core.components.ingest.ingest_component  import SimpleIngestComponent
from everi_ai_qgpt_core.server.ingest.ingest_service import IngestService
from everi_ai_qgpt_core.server.ingest.model import IngestedDoc
from everi_ai_qgpt_core.constants import PROJECT_ROOT_PATH

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IngestTextBody(BaseModel):
    file_name: str = Field(examples=["Avatar: The Last Airbender"])
    text: str = Field(
        examples=[
            "Avatar is set in an Asian and Arctic-inspired world in which some "
            "people can telekinetically manipulate one of the four elements—water, "
            "earth, fire or air—through practices known as 'bending', inspired by "
            "Chinese martial arts."
        ]
    )

class IngestResponse(BaseModel):
    object: Literal["list"]
    model: Literal["private-gpt"]
    data: list[IngestedDoc]

class GoogleDriveClient:    
    def __init__(self):
        # Load the client secret JSON file using project root path
        # json_file_path = "/home/srikar/QGPT_BE/QGPT/everi_ai_qgpt_core/tokenFolder/client_secret_35945508936-uothe1o4slnugbc3ghcjj4drqcnelvjh.apps.googleusercontent.com.json"
        # json_file_path = "/home/ubuntu/github/qgpt/everi_ai_qgpt_core/tokenFolder/client_secret_35945508936-uothe1o4slnugbc3ghcjj4drqcnelvjh.apps.googleusercontent.com.json"
        json_file_path = PROJECT_ROOT_PATH / "everi_ai_qgpt_core" / "tokenFolder" / "client_secret_35945508936-uothe1o4slnugbc3ghcjj4drqcnelvjh.apps.googleusercontent.com.json"
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        self.config = GoogleDriveConfig(**data)
        
        # Define scopes for Google Drive API
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']
        self.service = self._build_service()    
    
    def _build_service(self):
        # Check if token.json exists (stores user credentials after first login)
        credentials = None
        # token_path = "/home/srikar/QGPT_BE/QGPT/everi_ai_qgpt_core/tokenFolder/token.json"
        # token_path = "/home/ubuntu/github/qgpt/everi_ai_qgpt_core/tokenFolder/token.json"
        token_path = PROJECT_ROOT_PATH / "everi_ai_qgpt_core" / "tokenFolder" / "token.json"
        if os.path.exists(token_path):
            credentials = Credentials.from_authorized_user_file(token_path, self.scopes)

        # If no valid credentials, initiate OAuth flow
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(google.auth.transport.requests.Request())
            else:
                flow = InstalledAppFlow.from_client_config(
                    {"installed": self.config.installed.dict()},  # Convert config to dict
                    self.scopes
                )
                credentials = flow.run_local_server(port=0)
                # Save the credentials for future use
                with open(token_path, 'w') as token_file:
                    token_file.write(credentials.to_json())

        return build('drive', 'v3', credentials=credentials)

    def list_files(self, limit: int, mime_type: str = None) -> list:
        """List files from Google Drive with optional MIME type filter."""
        try:
            query = f"mimeType='{mime_type}' and trashed=false" if mime_type else "trashed=false"
            results = (
                self.service.files()
                .list(
                    pageSize=limit,
                    fields="files(id, name, mimeType, permissions)",
                    q=query
                )
                .execute()
            )
            return results.get("files", [])
        except HttpError as e:
            logger.error(f"Failed to list files: {str(e)}")
            raise Exception(f"Failed to list files: {str(e)}")

    def read_google_doc(self, file_id: str) -> str:
        """Read the content of a Google Doc as plain text."""
        try:
            # Export the Google Doc as plain text
            request = self.service.files().export_media(fileId=file_id, mimeType="text/plain")
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Decode the content to string
            file_content.seek(0)
            return file_content.read().decode("utf-8")
        
        except HttpError as e:
            if e.resp.status == 403:
                raise HttpError(e.resp, f"Permission denied or file not downloadable: {file_id}")
            elif e.resp.status == 404:
                raise HttpError(e.resp, f"File not found: {file_id}")
            else:
                raise HttpError(e.resp, f"Failed to read Google Doc {file_id}: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error reading Google Doc {file_id}: {str(e)}")

    def read_notebook(self, file_id: str) -> dict:
        """Read the content of a Jupyter Notebook (.ipynb) as JSON."""
        try:
            # Download the .ipynb file
            reques = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, reques)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            # Parse the JSON content
            file_content.seek(0)
            return json.load(file_content)
        except Exception as e:
            raise Exception(f"Failed to read notebook: {str(e)}")
    
    
    def transform_google_drive_data(self, limit: int = 5) -> List[Tuple[str, Path]]:
        """
        Transform Google Drive file data into a format compatible with bulk_ingest.
        Fetches files from Google Drive and saves their content to temporary files.
        
        Args:
            limit (int): Maximum number of files to fetch. Defaults to 5.
        
        Returns:
            List[Tuple[str, Path]]: List of tuples containing file names and Path objects.
        """
        try:
            # Fetch Google Drive files (assumed to return list of dicts with id, name, content)
            files = self.list_files(limit, mime_type="application/vnd.google-apps.document")
            files_filtered = []
            for file in files:
                data = self.read_google_doc(file["id"])
                files_filtered.append({
                    "id": file["id"],
                    "name": file["name"],
                    "content": data
                })
            file_paths = []

            for file in files_filtered:
                logger.info(file)
                # Validate file data
                if not all(key in file for key in ['name', 'content']):
                    logger.warning(f"Skipping file with missing data: {file.get('id', 'unknown')}")
                    continue

                # Sanitize file name for filesystem compatibility
                file_name = file['name'].replace('/', '_').replace('\\', '_').strip()
                if not file_name:
                    logger.warning(f"Skipping file with empty name: {file.get('id', 'unknown')}")
                    continue

                # Create a temporary file for the content
                with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', prefix=file_name) as temp_file:
                    # Write content to the temporary file (handle empty or None content)
                    content = file['content'] if file['content'] is not None else ''
                    temp_file.write(content.encode('utf-8'))
                    temp_file_path = Path(temp_file.name)

                # Store the original file name and temporary file path
                file_paths.append((file['name'], temp_file_path))
                logger.debug(f"Prepared file: {file['name']} -> {temp_file_path}")

            return file_paths

        except Exception as e:
            logger.error(f"Error transforming Google Drive data: {str(e)}")
            raise
    def load_files(self):
        files = self.list_files(limit = 5, mime_type="application/vnd.google-apps.document")
        content = []
        for file in files:
            try:
                data = self.read_google_doc(file["id"])
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
        return {"files": content}
        

    def insert_data(self) -> IngestResponse:
        """
        Fetch Google Drive data and ingest it using SimpleIngestComponent.
        """
        try:
            # file_paths = self.transform_google_drive_data(limit=5)
            # if not file_paths:
            #     logger.warning("No files were prepared for ingestion.")
            #     return
            # storage_context = StorageContext()
            # embed_type = EmbedType()  # Replace with actual embedding type
            # transform_components = []  # Replace with actual transformation components
            # simpleingestcomponent = SimpleIngestComponent(storage_context, embed_type, list[transform_components])
            # simpleingestcomponent.bulk_ingest(file_paths)
            file_ids = []
            request =  Request()
            files = self.load_files()
            for file in files:
                service = request.state.injector.get(IngestService)
                if len(body.file_name) == 0:
                    raise HTTPException(400, "No file name provided")
                ingested_documents = service.ingest_text(file.name, file.content)
                logger.info(ingested_documents)
                file_ids.append(file.id)
            # return IngestResponse(object="list", model="private-gpt", data=ingested_documents)
            return file_ids

        except Exception as e:
            logger.error(f"Error during data insertion: {str(e)}")
            raise
