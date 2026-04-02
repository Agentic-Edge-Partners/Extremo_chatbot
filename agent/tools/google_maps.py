"""Google Maps tools for place search, geocoding, route calculation, and event route planning."""

from __future__ import annotations

import json
import math
import os
import urllib.parse
import urllib.request

from langchain_core.tools import tool

# Maximum distance (km) a place can be from the location center
_MAX_RADIUS_KM = 15.0

# ---------------------------------------------------------------------------
# Activity type query hints — used to refine place search results
# ---------------------------------------------------------------------------

_ACTIVITY_TYPE_QUERIES: dict[str, list[str]] = {
    "natural_sights": [
        "viewpoint", "park", "nature reserve", "beach", "waterfall",
        "mountain", "hiking trail", "garden", "cliff", "forest",
    ],
    "cultural": [
        "museum", "historic site", "monument", "wine cellar", "castle",
        "palace", "church", "traditional market", "art gallery", "heritage",
    ],
    "restaurants": [
        "restaurant", "wine bar", "traditional food", "tavern", "seafood",
        "fine dining", "local cuisine", "tapas", "gastronomy",
    ],
    "venues": [
        "event space", "hotel meeting room", "quinta", "conference venue",
        "banquet hall", "retreat center", "manor house",
    ],
}

# ---------------------------------------------------------------------------
# Competitor / excluded activity keywords — these get filtered OUT of results
# ---------------------------------------------------------------------------

_EXCLUDED_KEYWORDS = [
    "cycling", "bicycle", "bike rental", "bike tour", "biking",
    "segway", "scooter", "e-bike", "tuk tuk", "tuk-tuk",
    "hop on hop off", "hop-on hop-off", "bus tour",
    "sliding", "slide",
]


def _maps_key() -> str | None:
    return os.getenv("GOOGLE_MAPS_API_KEY")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in km between two points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _geocode_location(location: str) -> tuple[float, float] | None:
    """Geocode a location string to (lat, lng). Returns None on failure."""
    api_key = _maps_key()
    if not api_key:
        return None
    encoded = urllib.parse.urlencode({"address": location, "key": api_key})
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{encoded}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
    except Exception:
        pass
    return None


def _is_excluded_place(place: dict) -> bool:
    """Check if a place matches any excluded competitor keywords."""
    name = (place.get("displayName", {}).get("text", "") or "").lower()
    summary = (place.get("editorialSummary", {}).get("text", "") or "").lower()
    types = [t.lower() for t in place.get("types", [])]
    combined = f"{name} {summary} {' '.join(types)}"
    return any(kw in combined for kw in _EXCLUDED_KEYWORDS)


# ---------------------------------------------------------------------------
# Place Search (Google Places API — New)
# ---------------------------------------------------------------------------

@tool
def search_places(
    query: str,
    location_bias: str = "Porto, Portugal",
    center_lat: float = 0.0,
    center_lng: float = 0.0,
    activity_type: str = "general",
) -> str:
    """Search for real places, venues, and landmarks using Google Maps.

    Use specific place-type queries for best results — e.g. 'seafood restaurants
    in Porto', 'museums in Porto', 'parks near Matosinhos'. Avoid vague queries
    like 'activities' or 'things to do'.

    Results are restricted to a 15 km radius from the center of the target
    location. Places outside this radius are automatically filtered out.
    Competitor activities (cycling tours, bike rentals, segway, scooter tours,
    tuk-tuk tours) are automatically excluded from results.

    Args:
        query: Specific place search, e.g. 'wine cellars Vila Nova de Gaia'
        location_bias: City or area to bias results toward
        center_lat: Latitude of the center point (0 = auto-geocode from location_bias)
        center_lng: Longitude of the center point (0 = auto-geocode from location_bias)
        activity_type: Filter results by type. Options:
            - 'natural_sights' — Viewpoints, parks, nature reserves, beaches, waterfalls
            - 'cultural' — Museums, historic sites, monuments, wine cellars, castles
            - 'restaurants' — Restaurants, wine bars, traditional food experiences
            - 'venues' — Event spaces, hotels with meeting rooms, quintas
            - 'general' — No filter (default)
    """
    api_key = _maps_key()
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY not set"

    # Resolve center coordinates for distance filtering
    if center_lat == 0.0 and center_lng == 0.0:
        coords = _geocode_location(location_bias)
        if coords:
            center_lat, center_lng = coords

    # Refine the query with activity type hints if applicable
    type_hints = _ACTIVITY_TYPE_QUERIES.get(activity_type, [])
    if type_hints and activity_type != "general":
        # Add the first few type hints to help bias the search
        hint_text = " OR ".join(type_hints[:3])
        search_query = f"{query} ({hint_text}) near {location_bias}"
    else:
        search_query = f"{query} near {location_bias}"

    url = "https://places.googleapis.com/v1/places:searchText"

    request_body: dict = {
        "textQuery": search_query,
        "maxResultCount": 15,
        "languageCode": "en",
    }

    # Use a 15 km circle bias when we have center coordinates
    if center_lat and center_lng:
        request_body["locationBias"] = {
            "circle": {
                "center": {"latitude": center_lat, "longitude": center_lng},
                "radius": _MAX_RADIUS_KM * 1000,  # metres
            }
        }

    body = json.dumps(request_body).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                "places.displayName,places.formattedAddress,"
                "places.location,places.types,places.rating,"
                "places.editorialSummary"
            ),
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return f"Error searching places: {e}"

    results = []
    for p in data.get("places", []):
        # Exclude competitor activities
        if _is_excluded_place(p):
            continue

        loc = p.get("location", {})
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        summary = p.get("editorialSummary", {}).get("text", "")

        # Filter out places beyond 15 km from center
        if lat and lng and center_lat and center_lng:
            dist = _haversine_km(center_lat, center_lng, lat, lng)
            if dist > _MAX_RADIUS_KM:
                continue

        results.append({
            "name": p.get("displayName", {}).get("text", "Unknown"),
            "address": p.get("formattedAddress", ""),
            "latitude": lat,
            "longitude": lng,
            "types": p.get("types", [])[:3],
            "rating": p.get("rating"),
            "summary": summary,
        })

    if not results:
        return "No places found for this query."
    return json.dumps(results[:10], indent=2)


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

@tool
def geocode_address(address: str) -> str:
    """Get the latitude and longitude for a given address.

    Args:
        address: The address or place name to geocode
    """
    api_key = _maps_key()
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY not set"

    encoded = urllib.parse.urlencode({"address": address, "key": api_key})
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{encoded}"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return f"Error geocoding: {e}"

    if data.get("status") != "OK" or not data.get("results"):
        return f"Could not geocode '{address}'"

    loc = data["results"][0]["geometry"]["location"]
    return json.dumps({
        "address": data["results"][0]["formatted_address"],
        "latitude": loc["lat"],
        "longitude": loc["lng"],
    })


# ---------------------------------------------------------------------------
# Route / Travel Duration (Google Routes API v2)
# ---------------------------------------------------------------------------

@tool
def get_travel_time(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    travel_mode: str = "DRIVE",
) -> str:
    """Calculate travel time and distance between two points using Google Maps Routes API.

    Args:
        origin_lat: Origin latitude
        origin_lng: Origin longitude
        dest_lat: Destination latitude
        dest_lng: Destination longitude
        travel_mode: DRIVE or WALK
    """
    api_key = _maps_key()
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY not set"

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    body = json.dumps({
        "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
        "travelMode": travel_mode,
        "routingPreference": "TRAFFIC_AWARE" if travel_mode == "DRIVE" else "ROUTING_PREFERENCE_UNSPECIFIED",
    }).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        return f"Error calculating route: {e}"

    routes = data.get("routes", [])
    if not routes:
        return "No route found between these points."

    route = routes[0]
    duration_sec = int(route.get("duration", "0s").rstrip("s"))
    distance_m = route.get("distanceMeters", 0)

    return json.dumps({
        "duration_minutes": round(duration_sec / 60, 1),
        "distance_km": round(distance_m / 1000, 1),
        "travel_mode": travel_mode,
    })


# ---------------------------------------------------------------------------
# Event Route Planner (with pickup/drop-off and optimization)
# ---------------------------------------------------------------------------

def _compute_route_leg(
    api_key: str,
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> dict:
    """Compute a single route leg between two coordinate pairs."""
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    body = json.dumps({
        "origin": {"location": {"latLng": {"latitude": origin[0], "longitude": origin[1]}}},
        "destination": {"location": {"latLng": {"latitude": destination[0], "longitude": destination[1]}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }).encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
        },
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())

    routes = data.get("routes", [])
    if not routes:
        return {"duration_minutes": 0, "distance_km": 0}

    route = routes[0]
    duration_sec = int(route.get("duration", "0s").rstrip("s"))
    distance_m = route.get("distanceMeters", 0)
    return {
        "duration_minutes": round(duration_sec / 60, 1),
        "distance_km": round(distance_m / 1000, 1),
    }


def _resolve_stop(stop: dict) -> tuple[float, float] | None:
    """Resolve a stop to (lat, lng) — use existing coords or geocode the name."""
    lat = stop.get("latitude")
    lng = stop.get("longitude")
    if lat and lng:
        return (lat, lng)
    name = stop.get("name", "")
    if name:
        return _geocode_location(name)
    return None


def _optimize_stop_order(
    api_key: str,  # unused — kept for future upgrade to driving-time optimization
    coords: list[tuple[float, float]],
) -> list[int]:
    """Find a good ordering for intermediate stops using nearest-neighbor heuristic.

    Uses straight-line (haversine) distance rather than actual driving time to
    avoid O(n^2) API calls. For typical corporate events (3-8 stops in the same
    region), this produces near-optimal results. A full driving-time matrix would
    be more accurate but requires n*(n-1)/2 Routes API calls.
    """
    if len(coords) <= 1:
        return list(range(len(coords)))

    n = len(coords)
    visited = [False] * n
    order = [0]
    visited[0] = True

    for _ in range(n - 1):
        current = order[-1]
        best_idx = -1
        best_dist = float("inf")
        for j in range(n):
            if not visited[j]:
                d = _haversine_km(
                    coords[current][0], coords[current][1],
                    coords[j][0], coords[j][1],
                )
                if d < best_dist:
                    best_dist = d
                    best_idx = j
        if best_idx >= 0:
            visited[best_idx] = True
            order.append(best_idx)

    return order


@tool
def plan_event_route(
    pickup: str,
    dropoff: str,
    stops_json: str,
    optimize: bool = True,
) -> str:
    """Plan an optimized event route with pickup and drop-off points.

    Creates a full driving route for a corporate event day. Takes a pickup location
    (start), drop-off location (end), and intermediate activity stops. Can
    optionally reorder stops to minimize total travel time.

    Returns the ordered itinerary with travel times between each stop, total
    duration, total distance, and a Google Maps URL for the route.

    Args:
        pickup: Pickup location (start of the route), e.g. 'Hotel Pestana Porto'
        dropoff: Drop-off location (end of the route), e.g. 'Hotel Pestana Porto'
            (often the same as pickup)
        stops_json: JSON string of intermediate stops. Each stop must have 'name'
            and optionally 'latitude'/'longitude'. Example:
            '[{"name": "Livraria Lello"}, {"name": "Caves Porto Calem",
              "latitude": 41.137, "longitude": -8.627}]'
        optimize: If true, reorder intermediate stops to minimize travel time.
            Defaults to true.
    """
    api_key = _maps_key()
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY not set"

    # Parse stops
    try:
        stops = json.loads(stops_json) if isinstance(stops_json, str) else stops_json
    except (json.JSONDecodeError, TypeError):
        return "Error: stops_json must be a valid JSON array"

    if not stops:
        return "Error: at least one intermediate stop is required"

    # Resolve all locations
    pickup_coords = _geocode_location(pickup)
    if not pickup_coords:
        return f"Error: could not geocode pickup location '{pickup}'"

    dropoff_coords = _geocode_location(dropoff)
    if not dropoff_coords:
        return f"Error: could not geocode drop-off location '{dropoff}'"

    resolved_stops = []
    for i, stop in enumerate(stops):
        coords = _resolve_stop(stop)
        if not coords:
            return f"Error: could not geocode stop #{i + 1}: '{stop.get('name', 'unknown')}'"
        resolved_stops.append({
            "name": stop.get("name", f"Stop {i + 1}"),
            "latitude": coords[0],
            "longitude": coords[1],
        })

    # Optimize order if requested
    if optimize and len(resolved_stops) > 1:
        stop_coords = [(s["latitude"], s["longitude"]) for s in resolved_stops]
        optimized_indices = _optimize_stop_order(api_key, stop_coords)
        resolved_stops = [resolved_stops[i] for i in optimized_indices]

    # Build the full route: pickup -> stops -> dropoff
    all_points = [
        {"name": pickup, "latitude": pickup_coords[0], "longitude": pickup_coords[1]},
        *resolved_stops,
        {"name": dropoff, "latitude": dropoff_coords[0], "longitude": dropoff_coords[1]},
    ]

    # Calculate leg-by-leg travel times
    legs = []
    total_duration = 0.0
    total_distance = 0.0

    for i in range(len(all_points) - 1):
        origin = (all_points[i]["latitude"], all_points[i]["longitude"])
        dest = (all_points[i + 1]["latitude"], all_points[i + 1]["longitude"])
        try:
            leg = _compute_route_leg(api_key, origin, dest)
        except Exception as e:
            leg = {"duration_minutes": 0, "distance_km": 0, "error": str(e)}

        legs.append({
            "from": all_points[i]["name"],
            "to": all_points[i + 1]["name"],
            "duration_minutes": leg["duration_minutes"],
            "distance_km": leg["distance_km"],
        })
        total_duration += leg["duration_minutes"]
        total_distance += leg["distance_km"]

    # Build Google Maps URL
    maps_stops = [
        {"name": p["name"], "latitude": p["latitude"], "longitude": p["longitude"]}
        for p in all_points
    ]
    maps_url = _build_maps_url(maps_stops)

    return json.dumps({
        "route_order": [p["name"] for p in all_points],
        "legs": legs,
        "total_driving_minutes": round(total_duration, 1),
        "total_distance_km": round(total_distance, 1),
        "optimized": optimize,
        "google_maps_url": maps_url,
    }, indent=2)


def _build_maps_url(stops: list[dict]) -> str:
    """Build a Google Maps directions URL from a list of stop dicts."""
    if len(stops) < 2:
        return ""

    def _place_str(stop: dict) -> str:
        if stop.get("latitude") and stop.get("longitude"):
            return f"{stop['latitude']},{stop['longitude']}"
        return stop.get("name", "Unknown")

    params = {
        "api": "1",
        "origin": _place_str(stops[0]),
        "destination": _place_str(stops[-1]),
        "travelmode": "driving",
    }

    if len(stops) > 2:
        waypoints = "|".join(_place_str(s) for s in stops[1:-1])
        params["waypoints"] = waypoints

    query_string = urllib.parse.urlencode(params)
    return f"https://www.google.com/maps/dir/?{query_string}"


# ---------------------------------------------------------------------------
# Google Maps URL Builder
# ---------------------------------------------------------------------------

@tool
def build_google_maps_url(stops_json: str) -> str:
    """Build a Google Maps directions URL that shows the full driving route between stops.
    The URL will render with the actual road path drawn on the map.

    Args:
        stops_json: JSON string of a list of stops. Each stop must have 'name'
            and optionally 'latitude'/'longitude'. Example:
            '[{"name": "Ribeira, Porto", "latitude": 41.14, "longitude": -8.61},
              {"name": "Livraria Lello", "latitude": 41.15, "longitude": -8.61}]'
    """
    try:
        stops = json.loads(stops_json) if isinstance(stops_json, str) else stops_json
    except (json.JSONDecodeError, TypeError):
        return "Error: stops_json must be a valid JSON array"

    if not stops or len(stops) < 2:
        return "Need at least 2 stops to build a route URL."

    return _build_maps_url(stops)
