"""Tools for creating and managing ad groups."""

from typing import Any, Dict

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def create_ad_group(
    customer_id: str,
    campaign_id: str,
    name: str,
    cpc_bid: float | None = None,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Creates a standard search ad group (ENABLED) in a campaign.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The numeric id of the parent campaign.
        name: A unique ad group name within the campaign.
        cpc_bid: Optional default max CPC bid in currency units
            (used with manual bidding).
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    campaign_service = client.get_service("CampaignService")
    op = client.get_type("AdGroupOperation")
    ad_group = op.create
    ad_group.name = name
    ad_group.campaign = campaign_service.campaign_path(
        utils.clean_customer_id(customer_id), campaign_id
    )
    ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
    if cpc_bid:
        ad_group.cpc_bid_micros = utils.micros(cpc_bid)
    return utils.mutate(
        "AdGroupService",
        "MutateAdGroupsRequest",
        "mutate_ad_groups",
        customer_id,
        [op],
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def update_ad_group(
    customer_id: str,
    ad_group_id: str,
    status: str | None = None,
    cpc_bid: float | None = None,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Updates an ad group's status and/or default max CPC bid.

    Args:
        customer_id: The Google Ads account.
        ad_group_id: The numeric id of the ad group.
        status: Optional new status: ENABLED, PAUSED, or REMOVED.
        cpc_bid: Optional new default max CPC bid in currency units.
        validate_only: If True, only validates the request.
    """
    if status is None and cpc_bid is None:
        raise ToolError("Provide at least one of status or cpc_bid.")
    client = utils.get_googleads_client()
    service = client.get_service("AdGroupService")
    op = client.get_type("AdGroupOperation")
    ad_group = op.update
    ad_group.resource_name = service.ad_group_path(
        utils.clean_customer_id(customer_id), ad_group_id
    )
    if status is not None:
        try:
            ad_group.status = client.enums.AdGroupStatusEnum[status.upper()]
        except KeyError:
            raise ToolError(
                f"Unknown status '{status}'. Use ENABLED, PAUSED, or REMOVED."
            )
    if cpc_bid is not None:
        ad_group.cpc_bid_micros = utils.micros(cpc_bid)
    utils.apply_update_mask(client, op, ad_group)
    return utils.mutate(
        "AdGroupService",
        "MutateAdGroupsRequest",
        "mutate_ad_groups",
        customer_id,
        [op],
        validate_only,
    )
