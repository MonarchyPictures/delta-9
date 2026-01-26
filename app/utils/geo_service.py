from geopy.geocoders import Nominatim
from geopy.distance import geodesic

class GeoService:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="intent_radar")

    def get_coordinates(self, location_name):
        """Convert location name to lat/long."""
        if not location_name or location_name.lower() in ["unknown", "none", "null"]:
            return None, None
            
        try:
            # Add timeout to avoid hanging
            location = self.geolocator.geocode(location_name, timeout=2)
            if location:
                return location.latitude, location.longitude
        except:
            pass
        return None, None

    def calculate_distance(self, coords1, coords2):
        """Calculate distance in km between two points."""
        if not coords1 or not coords2:
            return None
        return geodesic(coords1, coords2).km

    def is_within_radius(self, center_coords, target_coords, radius_km):
        """Check if target is within radius of center."""
        if not center_coords or not target_coords:
            return True # If unknown, keep it
        distance = geodesic(center_coords, target_coords).km
        return distance <= radius_km
