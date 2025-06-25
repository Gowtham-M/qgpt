"""
Maps Chat Service Module - Handles follow-up conversations about map locations
"""

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
import logging
from typing import List, Optional, Dict, Any
from injector import inject, singleton
from qgpt_core.settings.settings import Settings
from qgpt_core.server.chat.chat_service import ChatService
from qgpt_core.components.llm.llm_component import LLMComponent
from llama_index.core.llms import ChatMessage, MessageRole

# Configure logging
logger = logging.getLogger(__name__)

class Coordinates(BaseModel):
    """Geographic coordinates"""
    latitude: float = Field(..., description="Latitude of the location")
    longitude: float = Field(..., description="Longitude of the location")

class MapChatMessage(BaseModel):
    """Chat message model for map-related conversations"""
    role: str
    content: str

class MapChatRequest(BaseModel):
    """Request model for map chat endpoint"""
    messages: List[MapChatMessage]
    coordinates: Coordinates
    mode: str = "Maps"

class MapChatResponse(BaseModel):
    """Response model for map chat endpoint"""
    response: str

@singleton
class MapChatService:
    """Service for handling map-related chat conversations"""
    
    @inject
    def __init__(self, settings: Settings, chat_service: ChatService, llm_component: LLMComponent):
        self.settings = settings
        self.chat_service = chat_service
        self.llm_component = llm_componentasync 
    def process_message(self, request: MapChatRequest) -> MapChatResponse:
        """Process a map-related chat request"""
        try:
            # Convert to ChatMessage format
            messages = []
            
            # Add system message if not present
            if not any(msg.role == "system" for msg in request.messages):
                system_prompt = f"""You are a helpful assistant specializing in location information. 
You're discussing a location at coordinates ({request.coordinates.latitude}, {request.coordinates.longitude}).
Please answer questions to help real estate clients understand the area, such as nearby amenities, schools, parks, and transportation options."""
                
                messages.append(ChatMessage(role=MessageRole.SYSTEM, content=system_prompt))
            
            # Add all other messages
            for msg in request.messages:
                role = MessageRole.SYSTEM if msg.role == "system" else (
                    MessageRole.USER if msg.role == "user" else MessageRole.ASSISTANT
                )
                messages.append(ChatMessage(role=role, content=msg.content))
              # Use the LLM directly without RAG to avoid the 'rag' attribute error
            llm_response = self.llm_component.llm.chat(messages)
            return MapChatResponse(response=llm_response.message.content)
        
        except Exception as e:
            logger.error(f"Error in map chat: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to process map chat: {str(e)}")
