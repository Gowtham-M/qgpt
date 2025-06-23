from pydantic import BaseModel
from typing import List

class InstalledConfig(BaseModel):
    client_id: str
    project_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: str
    client_secret: str
    redirect_uris: List[str]

class GoogleDriveConfig(BaseModel):
    installed: InstalledConfig