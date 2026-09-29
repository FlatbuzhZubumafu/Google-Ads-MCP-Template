"""Tool for discovering the queryable fields of Google Ads resources."""

from typing import Any, Dict

from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_resource_metadata(resource_name: str) -> Dict[str, Any]:
    """Retrieves the selectable, filterable, and sortable fields for a
    specific Google Ads resource, including compatible metrics and segments.

    Use this tool to find out which fields you can select, filter by, or
    sort by when querying a specific resource (e.g., 'campaign',
    'ad_group') with the `search` tool. Metric and segment field names
    start with 'metrics.' and 'segments.' respectively.

    Do not guess fields — use this tool to discover them before
    constructing a query. Responses can be cached; they rarely change.

    Args:
        resource_name: The name of the Google Ads resource
            (e.g., 'campaign', 'ad_group').
    """
    ga_service = utils.get_googleads_service("GoogleAdsFieldService")
    client = utils.get_googleads_client()
    request = client.get_type("SearchGoogleAdsFieldsRequest")

    selectable = set()
    filterable = set()
    sortable = set()

    def collect(response):
        for field in response:
            if field.selectable:
                selectable.add(field.name)
            if field.filterable:
                filterable.add(field.name)
            if field.sortable:
                sortable.add(field.name)

    # Resource attributes
    request.query = (
        "SELECT name, selectable, filterable, sortable "
        f"WHERE name LIKE '{resource_name}.%' AND category = 'ATTRIBUTE'"
    )
    try:
        collect(ga_service.search_google_ads_fields(request=request))
    except Exception as e:
        utils.logger.warning("Attributes query failed: %s", e)

    # Metrics and segments selectable with this resource
    request.query = (
        "SELECT name, selectable, filterable, sortable "
        f"WHERE selectable_with CONTAINS ANY('{resource_name}')"
    )
    try:
        collect(ga_service.search_google_ads_fields(request=request))
    except Exception as e:
        utils.logger.warning("Metrics/segments query failed: %s", e)

    if not selectable:
        raise RuntimeError(
            f"No metadata found for resource '{resource_name}'. "
            "Check the resource name against the search tool's resource list."
        )

    return {
        "resource": resource_name,
        "selectable": sorted(selectable),
        "filterable": sorted(filterable),
        "sortable": sorted(sortable),
    }
