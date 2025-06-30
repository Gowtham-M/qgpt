from fastapi import APIRouter, Depends, HTTPException, Request
from qgpt_core.server.utils.auth import authenticated
import logging
from pydantic import BaseModel, Field
import requests
from typing import Optional, List, Dict, Any, Literal
import json
from qgpt_core.settings.settings import Settings
from injector import inject
import os
from pathlib import Path
from dotenv import load_dotenv

# Import Ollama client to use the LLM for analysis
from llama_index.core.llms import ChatMessage, MessageRole
from qgpt_core.server.chat.chat_service import ChatService
from qgpt_core.components.llm.llm_component import LLMComponent
from qgpt_core.server.maps.maps_chat import MapChatService, MapChatRequest, MapChatResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env files
# Try to load from both the project root and the current directory
root_dir = Path(__file__).parent.parent.parent.parent  # Project root directory
env_paths = [
    root_dir / ".env",                 # Project root .env
    root_dir / "qgpt_core" / ".env",   # qgpt_core module .env
    Path(__file__).parent / ".env"     # Current directory .env
]

for env_path in env_paths:
    if env_path.exists():
        logger.info(f"Loading environment variables from {env_path}")
        load_dotenv(env_path)
        
# Check if the API key was loaded
maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
if maps_api_key:
    logger.info("Google Maps API key found in environment variables")
else:
    logger.warning("Google Maps API key not found in environment variables")

maps_router = APIRouter(prefix="/v1/maps", dependencies=[Depends(authenticated)])


class LocationCoordinates(BaseModel):
    latitude: float = Field(..., description="Latitude of the location")
    longitude: float = Field(..., description="Longitude of the location")
    radius: Optional[int] = Field(1000, description="Radius around the coordinates to analyze (in meters)")


class LocationAnalysisRequest(BaseModel):
    coordinates: Optional[LocationCoordinates] = Field(None, description="Coordinates for location analysis")
    types: Optional[List[str]] = Field(None, description="Types of places to include in the analysis")
    mapsInfo: Optional[dict] = Field(None, description="Full Google Maps API response for the location, if available.")
    query: Optional[str] = Field(None, description="Arbitrary query for maps analysis (if not using coordinates)")


class PlaceDetails(BaseModel):
    place_id: str
    name: str
    types: List[str]
    vicinity: str
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    geometry: Dict[str, Any]
    
    
class LocationAnalysisResponse(BaseModel):
    places: List[PlaceDetails]
    summary: Dict[str, Any]
    analysis: Optional[str] = None


class MapsService:    
    @inject
    def __init__(self, settings: Settings, chat_service: ChatService, llm_component: LLMComponent):
        # First check environment variable directly (highest priority)
        env_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        
        # Then check settings if not in environment
        if env_api_key:
            self.api_key = env_api_key
            logger.info("Using Google Maps API key from environment variables")
        elif settings.maps and settings.maps.api_key:
            self.api_key = settings.maps.api_key
            logger.info("Using Google Maps API key from settings")
        else:
            # Fallback to a default value - in production this should prompt proper configuration
            logger.warning("Google Maps API key not found in settings or environment, using placeholder. Please configure a real API key.")
            self.api_key = "YOUR_GOOGLE_MAPS_API_KEY"  # Placeholder - won't work in production
            
        self.chat_service = chat_service
        self.llm_component = llm_component
        
    def get_nearby_places(self, location: LocationCoordinates, types: Optional[List[str]] = None) -> List[PlaceDetails]:
        """
        Get nearby places using Google Places API
        """
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        
        # Build the parameters
        params = {
            "location": f"{location.latitude},{location.longitude}",
            "radius": location.radius,
            "key": self.api_key
        }
        
        if types and len(types) > 0:
            params["type"] = "|".join(types)
            
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data["status"] != "OK" and data["status"] != "ZERO_RESULTS":
                logger.error(f"Error from Google Places API: {data['status']}")
                raise HTTPException(status_code=500, detail=f"Error from Google Places API: {data['status']}")
                
            places = []
            for place in data.get("results", []):
                place_details = PlaceDetails(
                    place_id=place["place_id"],
                    name=place["name"],
                    types=place["types"],
                    vicinity=place.get("vicinity", ""),
                    rating=place.get("rating"),
                    user_ratings_total=place.get("user_ratings_total"),
                    geometry=place["geometry"]
                )
                places.append(place_details)
                
            return places
            
        except requests.RequestException as e:
            logger.error(f"Error fetching nearby places: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error fetching nearby places: {str(e)}")
    
    async def analyze_location(self, request: LocationAnalysisRequest) -> LocationAnalysisResponse:
        """
        Analyze a location based on its coordinates and nearby places or provided mapsInfo or query
        """
        if request.mapsInfo:
            # Parse places from mapsInfo (assume same structure as Google Maps API response)
            places_data = request.mapsInfo.get("results", [])
            places = []
            for place in places_data:
                place_details = PlaceDetails(
                    place_id=place["place_id"],
                    name=place["name"],
                    types=place["types"],
                    vicinity=place.get("vicinity", ""),
                    rating=place.get("rating"),
                    user_ratings_total=place.get("user_ratings_total"),
                    geometry=place["geometry"]
                )
                places.append(place_details)
        elif request.coordinates:
            places = self.get_nearby_places(request.coordinates, request.types)
        elif request.query:
            # Try to geocode the query string
            geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {"address": request.query, "key": self.api_key}
            try:
                resp = requests.get(geocode_url, params=params)
                resp.raise_for_status()
                geo_data = resp.json()
                if geo_data["status"] == "OK" and geo_data["results"]:
                    loc = geo_data["results"][0]["geometry"]["location"]
                    coordinates = LocationCoordinates(latitude=loc["lat"], longitude=loc["lng"], radius=1000)
                    # Now proceed as if coordinates were provided
                    places = self.get_nearby_places(coordinates, request.types)
                    # Patch: set request.coordinates for prompt
                    request.coordinates = coordinates
                else:
                    return LocationAnalysisResponse(
                        places=[],
                        summary={"place_count": 0, "types_distribution": {}, "average_rating": 0, "rated_places_count": 0},
                        analysis=f"Could not geocode location: {request.query}"
                    )
            except Exception as e:
                logger.error(f"Error geocoding query '{request.query}': {str(e)}")
                return LocationAnalysisResponse(
                    places=[],
                    summary={"place_count": 0, "types_distribution": {}, "average_rating": 0, "rated_places_count": 0},
                    analysis=f"Error geocoding location: {str(e)}"
                )
        else:
            raise HTTPException(status_code=422, detail="Either coordinates, mapsInfo, or query must be provided.")
        
        # Create a summary of the location analysis
        types_count = {}
        avg_rating = 0.0
        rated_places = 0
        
        for place in places:
            for type_name in place.types:
                if type_name in types_count:
                    types_count[type_name] += 1
                else:
                    types_count[type_name] = 1
            
            if place.rating:
                avg_rating += place.rating
                rated_places += 1
        
        if rated_places > 0:
            avg_rating = avg_rating / rated_places
        
        summary = {
            "place_count": len(places),
            "types_distribution": types_count,
            "average_rating": avg_rating,
            "rated_places_count": rated_places
        }

        # Generate a prompt for the Ollama model to analyze the area
        prompt = f"""
You are a location analysis specialist. I've gathered data about a location at coordinates ({request.coordinates.latitude}, {request.coordinates.longitude}).

Here's what I found within a {request.coordinates.radius}m radius:

- {len(places)} places in total
- Average rating: {avg_rating:.1f} out of 5.0 (from {rated_places} rated places)

Top place categories:
"""
        
        # Add top categories
        sorted_types = sorted(types_count.items(), key=lambda x: x[1], reverse=True)[:5]
        for type_name, count in sorted_types:
            prompt += f"- {type_name}: {count}\n"
        
        # Add sample places
        prompt += "\nSome notable places include:\n"
        for place in places[:5]:
            prompt += f"- {place.name} ({', '.join(place.types[:2])}): {place.vicinity}"
            if place.rating:
                prompt += f" - Rating: {place.rating}/5.0 ({place.user_ratings_total} reviews)"
            prompt += "\n"
            
        prompt += "\nBased on this data, please provide a detailed analysis of this area. Include insights about the type of neighborhood, typical activities, demographic insights if possible, and an overall assessment of the area's character and purpose."        # Use the Ollama model to analyze the area
        try:
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content="You are a location analysis specialist who provides detailed, insightful analysis of geographic areas based on points of interest data."),
                ChatMessage(role=MessageRole.USER, content=prompt)
            ]
              # Use the LLM directly to avoid the 'rag' attribute error
            response = self.llm_component.llm.chat(messages)
            analysis = response.message.content
            logger.info(f"Successfully generated location analysis of length: {len(analysis)}")
            
            return LocationAnalysisResponse(
                places=places, 
                summary=summary,
                analysis=analysis
            )
            
        except Exception as e:
            logger.error(f"Error generating analysis with Ollama: {str(e)}")
            # Return results without the AI analysis
            return LocationAnalysisResponse(
                places=places, 
                summary=summary,
                analysis="Could not generate analysis due to an error."
            )


@maps_router.post("/analyze", response_model=LocationAnalysisResponse, summary="Analyze a location using its coordinates")
async def analyze_location(request: LocationAnalysisRequest, req: Request) -> LocationAnalysisResponse:
    """
    Analyze a location using Google Maps API and Ollama for analysis
    """
    try:
        # Get injector from request state
        injector = req.state.injector
        maps_service = injector.get(MapsService)
        
        # Analyze the location
        response = await maps_service.analyze_location(request)
        return response
        
    except Exception as e:
        logger.error(f"Error analyzing location: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing location: {str(e)}")


@maps_router.post("/chat", response_model=MapChatResponse, summary="Chat about a location analysis")
async def chat_location_analysis(request: MapChatRequest, req: Request) -> MapChatResponse:
    """
    Chat about a location analysis previously conducted
    """
    try:
        # Get injector from request state
        injector = req.state.injector
        maps_chat_service = injector.get(MapChatService)
        
        # Process the chat message
        response = await maps_chat_service.process_message(request)
        return response
        
    except Exception as e:
        logger.error(f"Error in location analysis chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in location analysis chat: {str(e)}")
