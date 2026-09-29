"""Tools for creating and managing ads."""

from typing import Any, Dict, List

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def create_responsive_search_ad(
    customer_id: str,
    ad_group_id: str,
    headlines: List[str],
    descriptions: List[str],
    final_url: str,
    path1: str | None = None,
    path2: str | None = None,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Creates a responsive search ad in PAUSED state (enable it with
    `set_ad_status` after review).

    Args:
        customer_id: The Google Ads account.
        ad_group_id: The numeric id of the ad group to place the ad in.
        headlines: 3 to 15 headlines, each at most 30 characters.
        descriptions: 2 to 4 descriptions, each at most 90 characters.
        final_url: The landing page URL.
        path1: Optional first display-URL path segment (max 15 chars).
        path2: Optional second display-URL path segment (max 15 chars,
            requires path1).
        validate_only: If True, only validates the request.
    """
    if not 3 <= len(headlines) <= 15:
        raise ToolError("Provide between 3 and 15 headlines.")
    if not 2 <= len(descriptions) <= 4:
        raise ToolError("Provide between 2 and 4 descriptions.")
    too_long = [h for h in headlines if len(h) > 30]
    if too_long:
        raise ToolError(f"Headlines over 30 characters: {too_long}")
    too_long = [d for d in descriptions if len(d) > 90]
    if too_long:
        raise ToolError(f"Descriptions over 90 characters: {too_long}")

    client = utils.get_googleads_client()
    ad_group_service = client.get_service("AdGroupService")
    op = client.get_type("AdGroupAdOperation")
    ad_group_ad = op.create
    ad_group_ad.ad_group = ad_group_service.ad_group_path(
        utils.clean_customer_id(customer_id), ad_group_id
    )
    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED

    ad = ad_group_ad.ad
    ad.final_urls.append(final_url)
    for text in headlines:
        asset = client.get_type("AdTextAsset")
        asset.text = text
        ad.responsive_search_ad.headlines.append(asset)
    for text in descriptions:
        asset = client.get_type("AdTextAsset")
        asset.text = text
        ad.responsive_search_ad.descriptions.append(asset)
    if path1:
        ad.responsive_search_ad.path1 = path1
        if path2:
            ad.responsive_search_ad.path2 = path2

    return utils.mutate(
        "AdGroupAdService",
        "MutateAdGroupAdsRequest",
        "mutate_ad_group_ads",
        customer_id,
        [op],
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def set_ad_status(
    customer_id: str,
    ad_group_id: str,
    ad_id: str,
    status: str,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Pauses, enables, or removes an ad.

    Args:
        customer_id: The Google Ads account.
        ad_group_id: The numeric id of the ad group containing the ad.
        ad_id: The numeric id of the ad.
        status: ENABLED, PAUSED, or REMOVED. REMOVED is permanent —
            confirm with the user before using it.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    service = client.get_service("AdGroupAdService")
    op = client.get_type("AdGroupAdOperation")
    ad_group_ad = op.update
    ad_group_ad.resource_name = service.ad_group_ad_path(
        utils.clean_customer_id(customer_id), ad_group_id, ad_id
    )
    try:
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum[status.upper()]
    except KeyError:
        raise ToolError(
            f"Unknown status '{status}'. Use ENABLED, PAUSED, or REMOVED."
        )
    utils.apply_update_mask(client, op, ad_group_ad)
    return utils.mutate(
        "AdGroupAdService",
        "MutateAdGroupAdsRequest",
        "mutate_ad_group_ads",
        customer_id,
        [op],
        validate_only,
    )
