# Google Maps Integration for QGPT

This feature adds Google Maps location analysis integration to the QGPT application, allowing users to analyze locations using both Google Maps API data and the Ollama LLM.

## Features Added

1. **Backend Integration**:
   - Created a new Maps API router at `/v1/maps/analyze`
   - Implemented Google Places API integration for location data
   - Connected the Maps API with Ollama for intelligent analysis

2. **Frontend Integration**:
   - Added a Google Maps component with location search
   - Integrated maps analysis into the chat interface
   - Added a dedicated maps modal for selecting and analyzing locations

3. **Settings Configuration**:
   - Added Google Maps API configuration options in settings
   - Created a maps-specific settings file for easy deployment

## How to Use

1. Click on the "Maps" button in the sidebar
2. Search for a location or click on the map
3. Adjust the analysis radius as needed
4. Click "Analyze This Location"
5. The AI will analyze the area and provide insights in the chat

## Configuration

1. Get a Google Maps API key with Places API enabled
2. Add the API key to `settings-maps-ollama.yaml` file
3. Set environment variable `PGPT_PROFILES=maps-ollama` when running the application

## Technical Implementation

- The backend uses FastAPI for the Maps API endpoints
- Google Maps JavaScript API for interactive map functionality
- Ollama LLM for AI-powered location analysis
- Integration with existing chat interface for seamless user experience

## Dependencies Added

- @react-google-maps/api: ^2.19.3
- use-places-autocomplete: ^4.0.1
