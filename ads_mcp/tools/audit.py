"""Read-only audit tools: conversion setup, campaign criteria, geo lookup.

These are always mounted (including in read-only mode) — they mutate
nothing.
"""

from typing import Any, Dict, List

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_conversion_actions(customer_id: str) -> List[Dict[str, Any]]:
    """Lists the account's conversion actions with category, type, status,
    and whether each is primary for optimization (primary_for_goal).

    Use this to check what Smart Bidding is actually optimizing toward —
    e.g. whether phone calls are primary and page-view style actions are
    secondary.

    Args:
        customer_id: The Google Ads account to inspect.
    """
    query = (
        "SELECT conversion_action.id, conversion_action.name, "
        "conversion_action.category, conversion_action.type, "
        "conversion_action.status, conversion_action.primary_for_goal, "
        "conversion_action.counting_type, "
        "conversion_action.phone_call_duration_seconds "
        "FROM conversion_action "
        "WHERE conversion_action.status != 'REMOVED'"
    )
    return utils.run_query(customer_id, query)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_campaign_criteria(
    customer_id: str, campaign_id: str
) -> List[Dict[str, Any]]:
    """Lists a campaign's targeting criteria: locations, proximity radii,
    ad schedules, devices, and negative criteria.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The campaign whose criteria to list.
    """
    query = (
        "SELECT campaign_criterion.criterion_id, campaign_criterion.type, "
        "campaign_criterion.negative, campaign_criterion.status, "
        "campaign_criterion.location.geo_target_constant, "
        "campaign_criterion.proximity.radius, "
        "campaign_criterion.proximity.radius_units, "
        "campaign_criterion.ad_schedule.day_of_week, "
        "campaign_criterion.ad_schedule.start_hour, "
        "campaign_criterion.ad_schedule.end_hour, "
        "campaign_criterion.device.type, "
        "campaign_criterion.keyword.text, "
        "campaign_criterion.keyword.match_type "
        "FROM campaign_criterion "
        f"WHERE campaign.id = {int(campaign_id)}"
    )
    return utils.run_query(customer_id, query)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def suggest_geo_targets(
    location_names: List[str],
    country_code: str = "US",
) -> List[Dict[str, Any]]:
    """Resolves human-readable location names (e.g. 'Phoenix, Arizona',
    'Gilbert, Arizona') to Google Ads geo target constant IDs, for use
    with add_location_targeting.

    Args:
        location_names: Location names to resolve.
        country_code: Two-letter country code to scope the lookup.
    """
    from google.ads.googleads.errors import GoogleAdsException

    client = utils.get_googleads_client()
    service = client.get_service("GeoTargetConstantService")
    request = client.get_type("SuggestGeoTargetConstantsRequest")
    request.locale = "en"
    request.country_code = country_code
    request.location_names.names.extend(location_names)
    try:
        response = service.suggest_geo_target_constants(request=request)
    except GoogleAdsException as ex:
        raise utils.to_tool_error(ex)

    results = []
    for suggestion in response.geo_target_constant_suggestions:
        gtc = suggestion.geo_target_constant
        results.append(
            {
                "search_term": suggestion.search_term,
                "id": gtc.id,
                "name": gtc.name,
                "canonical_name": gtc.canonical_name,
                "target_type": gtc.target_type,
                "resource_name": gtc.resource_name,
            }
        )
    if not results:
        raise ToolError(
            f"No geo targets found for {location_names} in {country_code}."
        )
    return results
