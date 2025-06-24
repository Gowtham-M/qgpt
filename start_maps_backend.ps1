# PowerShell script to start the QGPT backend with Google Maps API key
$env:GOOGLE_MAPS_API_KEY = "AIzaSyCcxJN30ArOo4yHON6oxSkthLXtT4B_p2o"
$env:PGPT_PROFILES = "maps-ollama"

# Run the backend
python -m qgpt_core
