# Google Maps Integration - Troubleshooting Guide

## Configuration Overview

The Google Maps integration requires an API key to be properly configured in both frontend and backend systems:

### Frontend Configuration

- The frontend already has the API key in `.env` file: `REACT_APP_GOOGLE_MAPS_API_KEY="YOUR_API_KEY"`
- This key is used by the React components to display maps and autocomplete functionality

### Backend Configuration

- The backend needs the API key to make calls to Google Places and other Google Maps APIs
- The configuration is in `settings-maps-ollama.yaml` under the `maps:` section

## Fix for "REQUEST_DENIED" Error

If you encounter a "REQUEST_DENIED" error from the Google Maps API, it means the backend doesn't have a valid API key. Here's how to fix it:

### Option 1: Set Environment Variable (Recommended)

Set the `GOOGLE_MAPS_API_KEY` environment variable before starting the backend:

```powershell
# PowerShell
$env:GOOGLE_MAPS_API_KEY = "YOUR_ACTUAL_API_KEY"
$env:PGPT_PROFILES = "maps-ollama"
python -m qgpt_core
```

```bash
# Bash/Linux
export GOOGLE_MAPS_API_KEY="YOUR_ACTUAL_API_KEY"
export PGPT_PROFILES="maps-ollama"
python -m qgpt_core
```

### Option 2: Use the Start Script

A start script has been provided to automatically set the required environment variables:

```
# PowerShell
./start_maps_backend.ps1
```

### Option 3: Modify the settings-maps-ollama.yaml directly

If you prefer not to use environment variables, you can update the API key directly in the settings file:

1. Open `settings-maps-ollama.yaml`
2. Find the `maps:` section
3. Replace the API key with a valid one:

```yaml
maps:
  api_key: "YOUR_ACTUAL_API_KEY" # Replace with your own API key
```

## Verification

To verify your setup is working correctly:

1. Start the backend using one of the methods above
2. Start the frontend using `npm start` in the qgpt_ui directory
3. Open the application in your browser
4. Try to use the location analysis feature
5. Check the backend logs for any API errors

If you continue to see REQUEST_DENIED errors, double check that:

1. The API key is valid and has the necessary permissions
2. The correct settings file is being loaded (check for PGPT_PROFILES)
3. The environment variable is properly set

## Getting a New Google Maps API Key

If you need a new API key, follow these steps:

1. Go to the Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select an existing one
3. Go to APIs & Services > Credentials
4. Create an API key
5. Enable the required Google Maps APIs:
   - Places API
   - Maps JavaScript API
   - Geocoding API
   - Any others needed by your application
