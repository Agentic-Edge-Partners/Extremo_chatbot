"""Extremo Ambiente assistant tools."""

from agent.tools.email_drafter import draft_email
from agent.tools.google_maps import (
    build_google_maps_url,
    geocode_address,
    get_travel_time,
    plan_event_route,
    search_places,
)

ALL_TOOLS = [
    search_places,
    geocode_address,
    get_travel_time,
    plan_event_route,
    build_google_maps_url,
    draft_email,
]
