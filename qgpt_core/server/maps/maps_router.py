from fastapi import APIRouter, Depends, HTTPException, Request
# Assuming authenticated is correctly imported from qgpt_core.server.utils.auth
from qgpt_core.server.utils.auth import authenticated
import logging
from pydantic import BaseModel, Field
import httpx # Use httpx for async requests
from typing import Optional, List, Dict, Any, Literal
import json
# Assuming these imports are correct based on user's environment
from qgpt_core.settings.settings import Settings
from injector import inject
import os
from pathlib import Path
from dotenv import load_dotenv

# Import Ollama client to use the LLM for analysis
from llama_index.core.llms import ChatMessage, MessageRole
from qgpt_core.server.chat.chat_service import ChatService
from qgpt_core.components.lllm.llm_component import LLMComponent
# Ensure MapChatRequest and MapChatResponse are defined or import them if they exist
from qgpt_core.server.maps.maps_chat import MapChatService, MapChatRequest, MapChatResponse


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env files
# Try to load from both the project root and the current directory
root_dir = Path(__file__).parent.parent.parent.parent # Project root directory
env_paths = [
    root_dir / ".env",          # Project root .env
    root_dir / "qgpt_core" / ".env", # qgpt_core module .env
    Path(__file__).parent / ".env"    # Current directory .env
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


# --- Pydantic Models ---
class LocationCoordinates(BaseModel):
    latitude: float = Field(..., description="Latitude of the location")
    longitude: float = Field(..., description="Longitude of the location")
    radius: Optional[int] = Field(1000, description="Radius around the coordinates to analyze (in meters)")


class LocationAnalysisRequest(BaseModel):
    coordinates: Optional[LocationCoordinates] = Field(None, description="Coordinates for location analysis")
    types: Optional[List[str]] = Field(None, description="Types of places to include in the analysis")
    mapsInfo: Optional[Dict[str, Any]] = Field(None, description="Full Google Maps API response for the location, if available.")
    query: Optional[str] = Field(None, description="Arbitrary query for maps analysis (if not using coordinates)")
    
    # New fields for distance calculation
    origin_query: Optional[str] = Field(None, description="Starting location for distance calculation (e.g., 'Hyderabad' or 'Charminar')")
    destination_query: Optional[str] = Field(None, description="Ending location for distance calculation (e.g., 'Bangalore' or 'Golconda Fort')")
    travel_mode: Literal["driving", "walking", "bicycling", "transit"] = Field("driving", description="Mode of travel for distance calculation")


class PlaceDetails(BaseModel):
    place_id: str
    name: str
    types: List[str]
    vicinity: str
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    geometry: Dict[str, Any]
    
    
class LocationAnalysisResponse(BaseModel):
    places: List[PlaceDetails] = [] # Initialize as empty list
    summary: Dict[str, Any] = {} # Initialize as empty dict
    analysis: Optional[str] = None
    
    # New fields for distance calculation response
    distance_km: Optional[float] = Field(None, description="Calculated distance in kilometers")
    duration_text: Optional[str] = Field(None, description="Human-readable duration text (e.g., '1 hour 30 mins')")
    origin_name: Optional[str] = Field(None, description="Resolved name of the origin location")
    destination_name: Optional[str] = Field(None, description="Resolved name of the destination location")
    
    # New field for flat list of nearest transit points (for UI marker rendering)
    nearest_transit: Optional[List[Dict[str, Any]]] = Field(None, description="List of nearest transit points with lat/lng/type for UI")


# --- MapsService Class ---
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
            self.api_key = "YOUR_Maps_API_KEY"  # Placeholder - won't work in production
            
        self.chat_service = chat_service
        self.llm_component = llm_component
        self.base_maps_url = "https://maps.googleapis.com/maps/api"

    async def get_nearby_places(self, location: LocationCoordinates, types: Optional[List[str]] = None) -> List[PlaceDetails]:
        """
        Get nearby places using Google Places API (Nearby Search) asynchronously.
        """
        url = f"{self.base_maps_url}/place/nearbysearch/json"
        
        # Build the parameters
        params = {
            "location": f"{location.latitude},{location.longitude}",
            "radius": location.radius,
            "key": self.api_key
        }
        
        if types and len(types) > 0:
            params["type"] = "|".join(types)
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                
                data = response.json()
                
                if data["status"] not in ["OK", "ZERO_RESULTS"]:
                    logger.error(f"Error from Google Places API (Nearby Search): {data['status']}")
                    # Propagate specific API error message if available, otherwise generic HTTP 500
                    raise HTTPException(status_code=500, detail=f"Error from Google Places API: {data['status']}")
                    
                places = []
                for place in data.get("results", []):
                    # Filter out malformed places without essential keys
                    if "place_id" not in place or "name" not in place or "geometry" not in place:
                        logger.warning(f"Skipping malformed place data from Nearby Search: {place}")
                        continue
                    place_details = PlaceDetails(
                        place_id=place["place_id"],
                        name=place["name"],
                        types=place.get("types", []), # Ensure types is a list, default to empty if missing
                        vicinity=place.get("vicinity", ""),
                        rating=place.get("rating"),
                        user_ratings_total=place.get("user_ratings_total"),
                        geometry=place["geometry"]
                    )
                    places.append(place_details)
                    
                return places
                
        except httpx.RequestError as e:
            logger.error(f"Error fetching nearby places: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error fetching nearby places: {str(e)}")
    
    async def get_coordinates_from_query(self, query: str) -> Optional[LocationCoordinates]:
        """
        Geocodes a query string to get coordinates asynchronously using Google Geocoding API.
        """
        geocode_url = f"{self.base_maps_url}/geocode/json"
        params = {"address": query, "key": self.api_key}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(geocode_url, params=params)
                resp.raise_for_status()
                geo_data = resp.json()
                if geo_data["status"] == "OK" and geo_data["results"]:
                    loc = geo_data["results"][0]["geometry"]["location"]
                    # Radius is not determined by geocoding itself, so we don't set it here.
                    # It will be applied in subsequent calls like get_nearby_places.
                    return LocationCoordinates(latitude=loc["lat"], longitude=loc["lng"])
                else:
                    logger.warning(f"Geocoding failed for query '{query}': {geo_data.get('status', 'Unknown status')}")
                    return None
        except httpx.RequestError as e:
            logger.error(f"Error geocoding query '{query}': {str(e)}")
            return None

    async def get_place_id_from_query(self, query: str) -> Optional[str]:
        """
        Uses Places API (Find Place from Text) to get a Place ID for a query string asynchronously.
        Falls back to Geocoding API for broad locations (cities, regions) if needed.
        """
        find_place_url = f"{self.base_maps_url}/place/findplacefromtext/json"
        params = {
            "input": query,
            "inputtype": "textquery",
            "fields": "place_id", # Requesting only place_id saves on billing
            "key": self.api_key
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(find_place_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if data["status"] == "OK" and data["candidates"]:
                    return data["candidates"][0]["place_id"]
                else:
                    logger.warning(f"Find Place API failed for query '{query}': {data.get('status', 'Unknown status')}")
                    # Fallback: Try Geocoding API for city/region
                    geo = await self.get_coordinates_from_query(query)
                    if geo:
                        # Use coordinates as a fallback for Distance Matrix API
                        return f"{geo.latitude},{geo.longitude}"
                    return None
        except httpx.RequestError as e:
            logger.error(f"Error finding place for query '{query}': {str(e)}")
            return None

    async def get_distance_between_places(self, origin_query: str, destination_query: str, travel_mode: str = "driving") -> Dict[str, Any]:
        """
        Calculates distance and duration between two locations using Google Distance Matrix API asynchronously.
        This function will first resolve origin and destination queries to Place IDs or coordinates.
        """
        # Resolve origin and destination queries to Place IDs or coordinates
        origin_id = await self.get_place_id_from_query(origin_query)
        destination_id = await self.get_place_id_from_query(destination_query)

        if not origin_id:
            logger.warning(f"Could not resolve origin query '{origin_query}' to a Place ID or coordinates.")
            return {"error": f"Could not find a valid origin for '{origin_query}'"}
        if not destination_id:
            logger.warning(f"Could not resolve destination query '{destination_query}' to a Place ID or coordinates.")
            return {"error": f"Could not find a valid destination for '{destination_query}'"}

        # Accept both place_id:... and lat,lng
        origins_param = origin_id if "," in origin_id else f"place_id:{origin_id}"
        destinations_param = destination_id if "," in destination_id else f"place_id:{destination_id}"

        distance_matrix_url = f"{self.base_maps_url}/distancematrix/json"
        params = {
            "origins": origins_param,
            "destinations": destinations_param,
            "mode": travel_mode,
            "key": self.api_key
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(distance_matrix_url, params=params)
                resp.raise_for_status()
                data = resp.json()

                if data["status"] == "OK" and data["rows"] and data["rows"][0]["elements"]:
                    element = data["rows"][0]["elements"][0]
                    if element["status"] == "OK":
                        distance = element["distance"]["value"] / 1000.0  # Convert meters to kilometers
                        duration = element["duration"]["text"]
                        origin_resolved_name = data["origin_addresses"][0] if data["origin_addresses"] else origin_query
                        destination_resolved_name = data["destination_addresses"][0] if data["destination_addresses"] else destination_query
                        return {
                            "origin_name": origin_resolved_name,
                            "destination_name": destination_resolved_name,
                            "distance_km": distance,
                            "duration_text": duration,
                            "status": "OK"
                        }
                    else:
                        logger.warning(f"Distance calculation element status for '{origin_query}' to '{destination_query}': {element['status']}")
                        return {"error": f"Distance calculation failed: {element['status']}"}
                else:
                    logger.warning(f"Distance Matrix API returned non-OK status or no elements for '{origin_query}' to '{destination_query}': {data.get('status', 'Unknown status')}")
                    return {"error": f"Distance Matrix API returned status: {data.get('status', 'Unknown status')}"}
        except httpx.RequestError as e:
            logger.error(f"Error calculating distance for '{origin_query}' to '{destination_query}': {str(e)}")
            return {"error": f"Error calculating distance: {str(e)}"}

    def get_commercial_place_types(self) -> list:
        """
        Returns a list of Google Places types that are typically associated with commercial zones.
        """
        return [
            "shopping_mall", "store", "supermarket", "department_store", "bank", "restaurant",
            "cafe", "bar", "night_club", "movie_theater", "gym", "pharmacy", "hospital",
            "lodging", "travel_agency", "real_estate_agency", "car_dealer", "car_rental",
            "car_repair", "car_wash", "electronics_store", "furniture_store", "hardware_store",
            "jewelry_store", "laundry", "lawyer", "insurance_agency", "accounting", "atm",
            "beauty_salon", "book_store", "bicycle_store", "clothing_store", "convenience_store",
            "doctor", "dry_cleaner", "florist", "hair_care", "home_goods_store", "liquor_store",
            "locksmith", "meal_delivery", "meal_takeaway", "painter", "pet_store", "plumber",
            "post_office", "real_estate_agency", "shoe_store", "spa", "travel_agency"
        ]

    async def analyze_location(self, request: LocationAnalysisRequest) -> LocationAnalysisResponse:
        """
        Analyze a location based on its coordinates and nearby places or provided mapsInfo or query,
        and handle distance calculation requests.
        """
        places: List[PlaceDetails] = []
        coordinates: Optional[LocationCoordinates] = None
        
        # Initialize response object with default empty values
        response_data = LocationAnalysisResponse()

        logger.info(f"analyze_location called with: {request.dict()}")

        # --- Primary Logic Branching: Handle Distance Calculation Request First ---
        if request.origin_query and request.destination_query:
            logger.info(f"[analyze_location] Routing to distance calculation: origin='{request.origin_query}', destination='{request.destination_query}', travel_mode='{request.travel_mode}'")
            distance_result = await self.get_distance_between_places(
                request.origin_query, request.destination_query, request.travel_mode
            )
            
            if "error" in distance_result:
                # If there's an error in distance calculation, populate analysis with error
                response_data.analysis = distance_result["error"]
                # Still populate origin/destination names for context in error response
                response_data.origin_name = request.origin_query
                response_data.destination_name = request.destination_query
                return response_data
            else:
                # Populate response with successful distance data
                response_data.distance_km = distance_result['distance_km']
                response_data.duration_text = distance_result['duration_text']
                response_data.origin_name = distance_result['origin_name']
                response_data.destination_name = distance_result['destination_name']

                # Use LLM to formulate a nice, user-friendly response for the distance
                distance_prompt = f"""
You are a helpful assistant providing travel information.
A user asked for the distance and travel time between two locations.
Here is the data:
Origin: {response_data.origin_name}
Destination: {response_data.destination_name}
Mode: {request.travel_mode}
Distance: {response_data.distance_km:.2f} km
Duration: {response_data.duration_text}

Please summarize this information for the user in a friendly and clear manner.
"""
                try:
                    messages = [
                        ChatMessage(role=MessageRole.SYSTEM, content="You are a helpful assistant providing travel information."),
                        ChatMessage(role=MessageRole.USER, content=distance_prompt)
                    ]
                    llm_response = self.llm_component.llm.chat(messages)
                    response_data.analysis = llm_response.message.content
                    logger.info("Successfully generated distance analysis summary using LLM.")
                except Exception as e:
                    logger.error(f"Error generating distance analysis summary with LLM: {str(e)}")
                    # Fallback to a programmatic summary if LLM fails
                    response_data.analysis = (
                        f"The distance from {response_data.origin_name} to {response_data.destination_name} "
                        f"by {request.travel_mode} is approximately {response_data.distance_km:.2f} km, "
                        f"taking about {response_data.duration_text}."
                    )
                return response_data

        # --- Existing Logic for Location Area Analysis (Nearby Places/Geocoding) ---
        # This block is executed ONLY if it's NOT a distance calculation request
        elif request.mapsInfo:
            logger.info("[analyze_location] Routing to area analysis: mapsInfo provided.")
            # If raw mapsInfo is provided, parse places from it
            places_data = request.mapsInfo.get("results", [])
            for place in places_data:
                # Basic validation for essential keys
                if "place_id" in place and "name" in place and "geometry" in place:
                    place_details = PlaceDetails(
                        place_id=place["place_id"],
                        name=place["name"],
                        types=place.get("types", []),
                        vicinity=place.get("vicinity", ""),
                        rating=place.get("rating"),
                        user_ratings_total=place.get("user_ratings_total"),
                        geometry=place["geometry"]
                    )
                    places.append(place_details)
                else:
                    logger.warning(f"Skipping malformed place data in mapsInfo: {place}")
            # If coordinates are also explicitly provided with mapsInfo, use them for the prompt later
            if request.coordinates:
                coordinates = request.coordinates

        elif request.coordinates:
            logger.info("[analyze_location] Routing to area analysis: coordinates provided.")
            # If coordinates are directly provided, fetch nearby places
            places = await self.get_nearby_places(request.coordinates, request.types)
            coordinates = request.coordinates # Keep coordinates for prompt generation
        
        elif request.query:
            logger.info("[analyze_location] Routing to area analysis: query provided.")
            # If only a query string is provided, first geocode it to get coordinates
            resolved_coordinates = await self.get_coordinates_from_query(request.query)
            if resolved_coordinates:
                # Use the resolved coordinates for a nearby search.
                # Use the radius from the original request, or default to 1000m if not specified.
                search_radius = request.coordinates.radius if request.coordinates and request.coordinates.radius else 1000
                # If commercial query, use commercial types
                types = self.get_commercial_place_types() if "commercial" in request.query.lower() and "zone" in request.query.lower() else request.types
                places = await self.get_nearby_places(LocationCoordinates(
                    latitude=resolved_coordinates.latitude,
                    longitude=resolved_coordinates.longitude,
                    radius=search_radius
                ), types)
                coordinates = LocationCoordinates( # Set coordinates for prompt use
                    latitude=resolved_coordinates.latitude,
                    longitude=resolved_coordinates.longitude,
                    radius=search_radius
                )
            else:
                # If geocoding fails, return an error response
                response_data.analysis = f"Could not geocode location: {request.query}"
                return response_data
        else:
            logger.warning("[analyze_location] No valid parameters provided. Raising HTTP 422.")
            # If none of the required parameters are provided, raise an HTTP error
            raise HTTPException(status_code=422, detail="Either coordinates, mapsInfo, query, or origin_query/destination_query must be provided.")

        # --- Common Summary Calculation for Nearby Places Analysis (if `places` list is populated) ---
        types_count = {}
        avg_rating = 0.0
        rated_places = 0
        
        for place in places:
            for type_name in place.types:
                types_count[type_name] = types_count.get(type_name, 0) + 1
            
            if place.rating is not None: # Ensure rating is not None before adding
                avg_rating += place.rating
                rated_places += 1
        
        if rated_places > 0:
            avg_rating = avg_rating / rated_places
        
        response_data.summary = {
            "place_count": len(places),
            "types_distribution": types_count,
            "average_rating": avg_rating,
            "rated_places_count": rated_places
        }
        response_data.places = places # Assign the found places to the response object

        # --- Find nearest airport, metro, railway station, and bus station if coordinates are available ---
        logger.info("[analyze_location] Starting nearest transit search block.")
        nearest_transit = {}
        nearest_transit_list = []  # <-- new: flat list for UI
        if coordinates:
            logger.info(f"[analyze_location] Coordinates for transit search: {coordinates}")
            transit_types = {
                "airport": ["airport"],
                "metro": ["subway_station"],
                "railway": ["train_station"],
                "bus": ["bus_station"]
            }
            for key, types in transit_types.items():
                logger.info(f"[analyze_location] Searching for nearest {key} with types {types}")
                try:
                    transit_places = await self.get_nearby_places(coordinates, types)
                    logger.info(f"[analyze_location] Found {len(transit_places) if transit_places else 0} places for {key}")
                    if transit_places:
                        nearest = transit_places[0]
                        logger.info(f"[analyze_location] Closest {key}: {nearest.name} ({nearest.vicinity})")
                        distance_info = await self.get_distance_between_places(
                            f"{coordinates.latitude},{coordinates.longitude}",
                            nearest.name,
                            request.travel_mode if hasattr(request, 'travel_mode') else "driving"
                        )
                        logger.info(f"[analyze_location] Distance info for {key}: {distance_info}")
                        # Extract lat/lng for UI
                        loc = nearest.geometry.get("location", {})
                        entry = {
                            "type": key,
                            "name": nearest.name,
                            "vicinity": nearest.vicinity,
                            "lat": loc.get("lat"),
                            "lng": loc.get("lng"),
                            "distance_km": distance_info.get("distance_km"),
                            "duration_text": distance_info.get("duration_text"),
                            "place_id": nearest.place_id
                        }
                        nearest_transit[key] = entry
                        nearest_transit_list.append(entry)
                    else:
                        logger.info(f"[analyze_location] No {key} found within search radius.")
                        nearest_transit[key] = None
                except Exception as e:
                    logger.error(f"Error finding nearest {key}: {str(e)}")
                    nearest_transit[key] = None
        # Attach to response
        logger.info(f"[analyze_location] nearest_transit dict: {nearest_transit}")
        if nearest_transit:
            response_data.summary["nearest_transit"] = nearest_transit
        logger.info(f"[analyze_location] nearest_transit_list (for UI): {nearest_transit_list}")
        if nearest_transit_list:
            response_data.nearest_transit = nearest_transit_list

        # --- Generate LLM analysis for the area if coordinates were successfully established ---
        if coordinates:
            # Prepare nearest transit info for the prompt
            nearest_transit = response_data.summary.get("nearest_transit", {})
            transit_section = "\nNearest Transit:\n"
            for key, label in zip(["airport", "metro", "railway", "bus"], ["Airport", "Metro", "Railway", "Bus Station"]):
                t = nearest_transit.get(key)
                if t:
                    transit_section += f"- {label}: {t['name']} ({t['vicinity']}), {t['distance_km']} km, {t['duration_text']}\n"
                else:
                    transit_section += f"- {label}: Not found within search radius\n"

            # Construct the prompt for area analysis based on gathered data
            prompt = f"""
You are a location analysis specialist. I've gathered data about a location at coordinates ({coordinates.latitude}, {coordinates.longitude}).

Here's what I found within a {coordinates.radius}m radius:

- {len(places)} places in total
- Average rating: {response_data.summary['average_rating']:.1f} out of 5.0 (from {response_data.summary['rated_places_count']} rated places)

Top place categories:
"""
            # Add top 5 most common place categories
            sorted_types = sorted(types_count.items(), key=lambda x: x[1], reverse=True)[:5]
            for type_name, count in sorted_types:
                prompt += f"- {type_name}: {count}\n"
            # Add a few notable sample places to the prompt
            prompt += "\nSome notable places include:\n"
            for place in places[:5]: # Take top 5 for the prompt
                place_types_str = ', '.join(place.types[:2]) if place.types else 'N/A'
                prompt += f"- {place.name} ({place_types_str}): {place.vicinity}"
                if place.rating is not None:
                    prompt += f" - Rating: {place.rating}/5.0 ({place.user_ratings_total} reviews)"
                prompt += "\n"
            # Add nearest transit section
            prompt += f"\n{transit_section}\n"

            # Add summary of nearest transit distances for LLM
            if nearest_transit:
                prompt += "\nNearest transit points and their distances from this location:\n"
                for key, label in zip(["airport", "metro", "railway", "bus"], ["Airport", "Metro", "Railway Station", "Bus Station"]):
                    t = nearest_transit.get(key)
                    if t and t.get('distance_km') is not None:
                        km = round(t['distance_km'], 1)
                        prompt += f"- Nearest {label}: {km} km away.\n"
                    elif t is None:
                        prompt += f"- Nearest {label}: Not found within search radius.\n"

            prompt += "\nBased on this data, please provide a detailed analysis of this area. Include insights about the type of neighborhood, typical activities, demographic insights if possible, and an overall assessment of the area's character and purpose."
            try:
                messages = [
                    ChatMessage(role=MessageRole.SYSTEM, content="You are a location analysis specialist who provides detailed, insightful analysis of geographic areas based on points of interest data."),
                    ChatMessage(role=MessageRole.USER, content=prompt)
                ]
                llm_response = self.llm_component.llm.chat(messages)
                response_data.analysis = llm_response.message.content
                logger.info(f"Successfully generated location area analysis of length: {len(response_data.analysis)} characters.")
                
            except Exception as e:
                logger.error(f"Error generating area analysis with Ollama: {str(e)}")
                response_data.analysis = "Could not generate area analysis due to an error."
        else:
            # This case covers when no coordinates were established (e.g., mapsInfo provided but no coord, or geocoding failed)
            # and it wasn't a distance query.
            if not (request.origin_query and request.destination_query): # Ensure it wasn't a distance query that filled 'analysis'
                response_data.analysis = "No area analysis was performed as no specific location was identified for proximity search or direct mapsInfo was provided without coordinates."

        # --- Commercial Zone Grouping and LLM Summary ---
        if request.query and "commercial" in request.query.lower() and "zone" in request.query.lower() and places:
            # Group places by vicinity (or use geometry/location if needed)
            from collections import defaultdict
            zone_groups = defaultdict(list)
            for place in places:
                key = place.vicinity if place.vicinity else place.name
                zone_groups[key].append(place)
            # Prepare a summary for LLM
            zone_summary = "\n".join([
                f"- {vicinity}: {len(places)} commercial places (e.g., {', '.join([p.name for p in places[:3]])})"
                for vicinity, places in sorted(zone_groups.items(), key=lambda x: len(x[1]), reverse=True)[:5]
            ])
            prompt = f"""
You are a location analysis expert. Given the following data for commercial places within a {coordinates.radius}m radius of {request.query} (lat: {coordinates.latitude}, lng: {coordinates.longitude}):

Top commercial zones identified:\n{zone_summary}\n\nPlease summarize the primary commercial zones, their significance, and what types of businesses are most common in each."
"""
            try:
                messages = [
                    ChatMessage(role=MessageRole.SYSTEM, content="You are a location analysis expert."),
                    ChatMessage(role=MessageRole.USER, content=prompt)
                ]
                llm_response = self.llm_component.llm.chat(messages)
                response_data.analysis = llm_response.message.content
                logger.info("Successfully generated commercial zone summary using LLM.")
            except Exception as e:
                logger.error(f"Error generating commercial zone summary with LLM: {str(e)}")
                response_data.analysis = f"Top commercial zones: {zone_summary}"
            return response_data

        # --- Find nearest airport, metro, and railway station, and bus station if coordinates are available ---
        nearest_transit = {}
        if coordinates:
            transit_types = {
                "airport": ["airport"],
                "metro": ["subway_station"],
                "railway": ["train_station"],
                "bus": ["bus_station"]
            }
            for key, types in transit_types.items():
                try:
                    transit_places = await self.get_nearby_places(coordinates, types)
                    if transit_places:
                        # Take the closest one (first in the list)
                        nearest = transit_places[0]
                        # Calculate distance from input location to this place
                        distance_info = await self.get_distance_between_places(
                            f"{coordinates.latitude},{coordinates.longitude}",
                            nearest.name,
                            request.travel_mode if hasattr(request, 'travel_mode') else "driving"
                        )
                        nearest_transit[key] = {
                            "name": nearest.name,
                            "vicinity": nearest.vicinity,
                            "distance_km": distance_info.get("distance_km"),
                            "duration_text": distance_info.get("duration_text"),
                            "place_id": nearest.place_id
                        }
                    else:
                        nearest_transit[key] = None
                except Exception as e:
                    logger.error(f"Error finding nearest {key}: {str(e)}")
                    nearest_transit[key] = None
        # Attach to response
        if nearest_transit:
            response_data.summary["nearest_transit"] = nearest_transit

        return response_data


# --- FastAPI Endpoints ---
@maps_router.post("/analyze", response_model=LocationAnalysisResponse, summary="Analyze a location or calculate distance between two locations")
async def analyze_location(request: LocationAnalysisRequest, req: Request) -> LocationAnalysisResponse:
    """
    Analyzes a location using Google Maps API for nearby places and Ollama for analysis,
    OR calculates the distance and travel time between two specified locations.
    Now supports free-form queries by using the LLM to extract intent and parameters.
    """
    try:
        injector = req.state.injector
        maps_service = injector.get(MapsService)
        llm_component = maps_service.llm_component

        logger.info(f"/analyze endpoint received request: {request.dict()}")

        # If the request is not structured, but has a free-form query, use LLM to extract intent/parameters
        if (
            request.query and not (
                request.origin_query and request.destination_query
            ) and not request.coordinates and not request.mapsInfo
        ):
            extraction_prompt = f"""
You are an AI assistant that extracts structured information from user queries about maps, locations, and distances.
Given the following question, return a JSON object with any of these keys if possible:
- origin_query (for distance queries)
- destination_query (for distance queries)
- coordinates (object with latitude, longitude, and optional radius)
- types (list of place types)
If the question is about the distance between two places, extract both origin_query and destination_query.
If the question is about a location or area, extract coordinates if possible, or just leave the query.
If you cannot extract any, return an empty JSON object.

Question: {request.query}
"""
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content="You are an AI assistant that extracts structured information from user queries about maps, locations, and distances."),
                ChatMessage(role=MessageRole.USER, content=extraction_prompt)
            ]
            llm_response = llm_component.llm.chat(messages)
            logger.info(f"{llm_response} 510")
            import re
            try:
                llm_content = llm_response.message.content.strip()
                # Remove all markdown code block markers (``` and ```json) from any line
                llm_content = '\n'.join(
                    line for line in llm_content.splitlines()
                    if not line.strip().startswith('```')
                ).strip()
                logger.info("LLM response for extraction (cleaned): " + llm_content)
                # Extract the first JSON object from the response
                match = re.search(r'\{[\s\S]*?\}', llm_content)
                if match:
                    json_str = match.group(0)
                    extracted = json.loads(json_str)
                    logger.info(f"LLM extracted fields: {extracted}")
                else:
                    logger.error("No JSON object found in LLM response.")
                    extracted = {}
            except Exception as e:
                logger.error(f"Error parsing LLM extraction response: {e}")
                extracted = {}
            logger.info(f"LLM extracted fields: {extracted}")
            # Build a new request object with extracted fields
            new_request_data = request.dict()
            if extracted.get("origin_query") and extracted.get("destination_query"):
                logger.info("LLM extracted distance calculation parameters.")
                new_request_data["origin_query"] = extracted["origin_query"]
                new_request_data["destination_query"] = extracted["destination_query"]
                if "travel_mode" in extracted:
                    new_request_data["travel_mode"] = extracted["travel_mode"]
            if extracted.get("coordinates"):
                coords = extracted["coordinates"]
                new_request_data["coordinates"] = coords
            if extracted.get("types"):
                new_request_data["types"] = extracted["types"]
            if extracted.get("query"):
                new_request_data["query"] = extracted["query"]
            # Reconstruct the request object so the correct logic branch is triggered
            request = LocationAnalysisRequest(**new_request_data)
            logger.info(f"Request after LLM extraction: {request.dict()}")

        response = await maps_service.analyze_location(request)
        logger.info(f"/analyze endpoint response: {response}")
        return response

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in /analyze endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@maps_router.post("/chat", response_model=MapChatResponse, summary="Chat about a location analysis")
async def chat_location_analysis(request: MapChatRequest, req: Request) -> MapChatResponse:
    """
    Chat about a location analysis previously conducted or perform a new one through chat.
    This endpoint would typically interact with an LLM that can use the /analyze endpoint as a tool.
    """
    try:
        # Get injector from request state
        injector = req.state.injector
        maps_chat_service = injector.get(MapChatService)
        
        # Process the chat message (this likely involves LLM function calling to /analyze)
        response = await maps_chat_service.process_message(request)
        return response
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled error in /chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred in chat: {str(e)}")