from typing import Literal

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
import yaml
from pathlib import Path 
from qgpt_core.server.utils.auth import authenticated

config_router = APIRouter(prefix="/v1", dependencies=[Depends(authenticated)])

BASE_DIR = Path(__file__).resolve().parent  # Directory of the current script

ROOT_DIR = BASE_DIR.parent.parent.parent 
config_file_path = ROOT_DIR / "settings-ollama.yaml"
# Load current config
def load_config():
    print(f"Loading config from: {config_file_path}")  
    with open(config_file_path, "r") as f:
        return yaml.safe_load(f)

# Save updated config
def save_config(config):
    with open(config_file_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

class ConfigResponse(BaseModel):
    llm_model: str
    embedding_model: str

class UpdateConfigBody(BaseModel):
    llmModel: str
    embeddingModel: str 
    class Config:
        extra = "allow"

class UpdateConfigResponse(BaseModel):
    message: str

@config_router.get("/config", tags=["Configuration"])
def get_config(request: Request) -> ConfigResponse:
    """Returns the current configuration from the YAML file."""
    config = load_config()
    llm=config["ollama"]["llm_model"]
    embed=config["ollama"]["embedding_model"]
    if ':' not in config["ollama"]["llm_model"]:
        llm=config["ollama"]["llm_model"]+':latest'
    if ':' not in config["ollama"]["embedding_model"]:
        embed=config["ollama"]["embedding_model"]+':latest'
    return ConfigResponse(
       
            
        llm_model=llm,
        embedding_model=embed,
    )

@config_router.put("/config", tags=["Configuration"])
def update_config(request: Request, body: UpdateConfigBody) -> UpdateConfigResponse:
    """Updates the configuration in the YAML file."""
    try:
        # config = load_config()
        # config["ollama"]["llm_model"] = body.llmModel
        # config["ollama"]["embedding_model"] = body.embeddingModel
        # save_config(config)
        return UpdateConfigResponse(message="Configuration updated successfully(commented out)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))