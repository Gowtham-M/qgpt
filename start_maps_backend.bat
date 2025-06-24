@echo off
REM Batch script to start the QGPT backend with Google Maps API key
set GOOGLE_MAPS_API_KEY=AIzaSyCcxJN30ArOo4yHON6oxSkthLXtT4B_p2o
set PGPT_PROFILES=maps-ollama

REM Run the backend
python -m qgpt_core
