# Start the QGPT backend with the maps-ollama profile and required environment variables
$env:PGPT_PROFILES = "maps-ollama"
$env:GOOGLE_MAPS_API_KEY = "AIzaSyCcxJN30ArOo4yHON6oxSkthLXtT4B_p2o"

# Run the app on port 8000 (to match the frontend's expected port)
python -m qgpt_core
