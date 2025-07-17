import React, { useState, useCallback } from "react";
import { GoogleMap, useJsApiLoader, Marker } from "@react-google-maps/api";
import { analyzeLocation } from "./api.ts";
import ReactShowdown from "react-showdown";

// Declare Google Maps types to fix typing errors
declare global {
  interface Window {
    google: any;
  }
}

const containerStyle = {
  width: "100%",
  height: "400px",
};

interface MapsComponentProps {
  onLocationAnalyzed: (analysisData: any) => void;
  isLoading: boolean;
  setLoading: (isLoading: boolean) => void;
  centerCoords?: LatLngLiteral | null; // NEW PROP
}

interface LatLngLiteral {
  lat: number;
  lng: number;
}

interface AnalysisResult {
  places: Array<any>;
  summary: {
    place_count: number;
    types_distribution: Record<string, number>;
    average_rating: number;
    rated_places_count: number;
  };
  analysis: string;
}

function MapsComponent({
  onLocationAnalyzed,
  isLoading,
  setLoading,
  centerCoords, // NEW PROP
}: MapsComponentProps) {
  const [libraries] = useState<string[]>(["places"]);
  const [center, setCenter] = useState<LatLngLiteral>({
    lat: 37.7749,
    lng: -122.4194,
  }); // Default to San Francisco
  const [markerPosition, setMarkerPosition] = useState<LatLngLiteral | null>(
    null
  );
  const [radius, setRadius] = useState(1000);
  const [mapInstance, setMapInstance] = useState<any>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null
  );
  const { isLoaded } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey:
      process.env.REACT_APP_GOOGLE_MAPS_API_KEY ||
      "AIzaSyCcxJN30ArOo4yHON6oxSkthLXtT4B_p2o",
    libraries: libraries as any,
  });

  const onMapClick = useCallback((e: any) => {
    const newPosition: LatLngLiteral = {
      lat: e.latLng.lat(),
      lng: e.latLng.lng(),
    };
    setMarkerPosition(newPosition);
    setAnalysisResult(null); // Reset analysis when location changes
  }, []);

  const onMapLoad = useCallback((map: any) => {
    setMapInstance(map);
  }, []);

  const handleAnalyzeLocation = async () => {
    if (!markerPosition) {
      alert("Please select a location on the map first.");
      return;
    }

    try {
      setLoading(true);
      const analysisData = await analyzeLocation(
        markerPosition.lat,
        markerPosition.lng,
        radius
      );

      setAnalysisResult(analysisData);
      onLocationAnalyzed(analysisData);
    } catch (error) {
      console.error("Failed to analyze location:", error);
      alert("Failed to analyze location. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Handle location search
  const handleLocationSearch = (address: string) => {
    if (!mapInstance || !address) return;

    const geocoder = new window.google.maps.Geocoder();

    geocoder.geocode({ address }, (results: any, status: string) => {
      if (status === "OK" && results && results[0]) {
        const location = results[0].geometry.location;
        const newCenter = {
          lat: location.lat(),
          lng: location.lng(),
        };
        setCenter(newCenter);
        setMarkerPosition(newCenter);
        mapInstance.panTo(location);
        setAnalysisResult(null); // Reset analysis when location changes
      } else {
        alert("Location not found");
      }
    });
  };

  // Effect: update center and marker if centerCoords prop changes
  React.useEffect(() => {
    if (
      centerCoords &&
      (centerCoords.lat !== center.lat || centerCoords.lng !== center.lng)
    ) {
      setCenter(centerCoords);
      setMarkerPosition(centerCoords);
      if (mapInstance) {
        mapInstance.panTo(centerCoords);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [centerCoords, center.lat, center.lng, mapInstance]);

  return isLoaded ? (
    <div className="maps-container">
      <div className="maps-controls mb-3">
        <div className="input-group">
          <input
            type="text"
            className="form-control"
            placeholder="Search for a location"
            onChange={(e) => {}}
            onKeyPress={(e) => {
              if (e.key === "Enter") {
                handleLocationSearch(e.currentTarget.value);
              }
            }}
          />
          <button
            className="btn btn-primary"
            onClick={() => {
              const input = document.querySelector(
                ".maps-controls input"
              ) as HTMLInputElement;
              if (input) {
                handleLocationSearch(input.value);
              }
            }}
          >
            Search
          </button>
        </div>
      </div>

      <div className="mb-3">
        <label htmlFor="radius" className="form-label">
          Analysis radius (meters): {radius}
        </label>
        <input
          type="range"
          className="form-range"
          id="radius"
          min="100"
          max="5000"
          step="100"
          value={radius}
          onChange={(e) => setRadius(parseInt(e.target.value))}
        />
      </div>

      <GoogleMap
        mapContainerStyle={containerStyle}
        center={center}
        zoom={14}
        onClick={onMapClick}
        onLoad={onMapLoad}
      >
        {markerPosition && <Marker position={markerPosition} />}
      </GoogleMap>

      <div className="mt-3">
        <button
          className="btn btn-success w-100"
          onClick={handleAnalyzeLocation}
          disabled={!markerPosition || isLoading}
        >
          {isLoading ? "Analyzing..." : "Analyze This Location"}
        </button>
        <small className="text-muted">
          Click on the map to set a location for analysis
        </small>
      </div>

      {analysisResult && (
        <div className="analysis-results mt-4">
          <h5>Analysis Results</h5>
          <div className="card">
            <div className="card-body">
              <h6>Ollama AI Analysis:</h6>
              <div className="ai-analysis">
                <ReactShowdown markdown={analysisResult.analysis} />
              </div>
              <hr />
              <div className="statistics">
                <small>
                  <strong>{analysisResult.places.length} places found</strong> |
                  Average rating:{" "}
                  {analysisResult.summary.average_rating.toFixed(1)}/5.0 (from{" "}
                  {analysisResult.summary.rated_places_count} ratings)
                </small>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  ) : (
    <div>Loading Maps...</div>
  );
}

export default React.memo(MapsComponent);
