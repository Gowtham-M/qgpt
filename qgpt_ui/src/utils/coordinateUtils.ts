// Utility to detect and extract coordinates from a string like "analyse 17.544, 70.343"
export function extractCoordinatesFromText(text: string): { lat: number, lng: number } | null {
  // Regex: match 'analyse' (case-insensitive), optional whitespace, then two floats separated by comma/space
  const regex = /analyse\s+([-+]?\d{1,3}(?:\.\d+)?)[,\s]+([-+]?\d{1,3}(?:\.\d+)?)/i;
  const match = text.match(regex);
  if (match) {
    const lat = parseFloat(match[1]);
    const lng = parseFloat(match[2]);
    if (!isNaN(lat) && !isNaN(lng)) {
      return { lat, lng };
    }
  }
  return null;
}
