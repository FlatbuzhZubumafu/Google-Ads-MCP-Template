"""Tools for creating and managing campaigns."""

from typing import Any, Dict

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp

_BIDDING_STRATEGIES = (
    "MANUAL_CPC",
    "MAXIMIZE_CLICKS",
    "MAXIMIZE_CONVERSIONS",
    "MAXIMIZE_CONVERSION_VALUE",
)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def create_campaign(
    customer_id: str,
    name: str,
    budget_resource_name: str,
    channel_type: str = "SEARCH",
    bidding_strategy: str = "MAXIMIZE_CLICKS",
    target_cpa: float | None = None,
    target_roas: float | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Creates a new campaign in PAUSED state (so it never spends money
    before a human reviews and enables it). Create a budget first with
    `create_campaign_budget`.

    Args:
        customer_id: The Google Ads account.
        name: A unique campaign name.
        budget_resource_name: Resource name returned by
            create_campaign_budget (customers/123/campaignBudgets/456).
        channel_type: Advertising channel, e.g. SEARCH or DISPLAY
            (default SEARCH).
        bidding_strategy: One of MANUAL_CPC, MAXIMIZE_CLICKS,
            MAXIMIZE_CONVERSIONS, MAXIMIZE_CONVERSION_VALUE.
        target_cpa: Optional target cost-per-action in currency units
            (only with MAXIMIZE_CONVERSIONS).
        target_roas: Optional target return on ad spend, e.g. 3.5
            (only with MAXIMIZE_CONVERSION_VALUE).
        start_date: Optional start date (YYYY-MM-DD).
        end_date: Optional end date (YYYY-MM-DD).
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    op = client.get_type("CampaignOperation")
    campaign = op.create
    campaign.name = name
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign.campaign_budget = budget_resource_name
    # Required declaration on newer API versions; guarded for older ones.
    try:
        campaign.contains_eu_political_advertising = (
            client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
        )
    except AttributeError:
        pass
    try:
        campaign.advertising_channel_type = (
            client.enums.AdvertisingChannelTypeEnum[channel_type.upper()]
        )
    except KeyError:
        raise ToolError(f"Unknown channel_type '{channel_type}'.")

    strategy = bidding_strategy.upper()
    if strategy == "MANUAL_CPC":
        campaign.manual_cpc.enhanced_cpc_enabled = False
    elif strategy == "MAXIMIZE_CLICKS":
        client.copy_from(
            campaign.target_spend, client.get_type("TargetSpend")
        )
    elif strategy == "MAXIMIZE_CONVERSIONS":
        max_conv = client.get_type("MaximizeConversions")
        if target_cpa:
            max_conv.target_cpa_micros = utils.micros(target_cpa)
        client.copy_from(campaign.maximize_conversions, max_conv)
    elif strategy == "MAXIMIZE_CONVERSION_VALUE":
        max_value = client.get_type("MaximizeConversionValue")
        if target_roas:
            max_value.target_roas = float(target_roas)
        client.copy_from(campaign.maximize_conversion_value, max_value)
    else:
        raise ToolError(
            f"Unknown bidding_strategy '{bidding_strategy}'. "
            f"Use one of: {_BIDDING_STRATEGIES}"
        )

    if campaign.advertising_channel_type == (
        client.enums.AdvertisingChannelTypeEnum.SEARCH
    ):
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        campaign.network_settings.target_content_network = False

    if start_date:
        campaign.start_date = start_date.replace("-", "")
    if end_date:
        campaign.end_date = end_date.replace("-", "")

    return utils.mutate(
        "CampaignService",
        "MutateCampaignsRequest",
        "mutate_campaigns",
        customer_id,
        [op],
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def set_campaign_target_cpa(
    customer_id: str,
    campaign_id: str,
    target_cpa: float,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Sets (or updates) the target CPA on a campaign that uses the
    Maximize Conversions bidding strategy.

    Only do this once the campaign has ~30+ conversions of history;
    setting a tCPA too early or too low throttles delivery.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The campaign to update.
        target_cpa: Target cost-per-action in the account's currency
            units (e.g. 85.0).
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    service = client.get_service("CampaignService")
    op = client.get_type("CampaignOperation")
    campaign = op.update
    campaign.resource_name = service.campaign_path(
        utils.clean_customer_id(customer_id), campaign_id
    )
    campaign.maximize_conversions.target_cpa_micros = utils.micros(target_cpa)
    utils.apply_update_mask(client, op, campaign)
    return utils.mutate(
        "CampaignService",
        "MutateCampaignsRequest",
        "mutate_campaigns",
        customer_id,
        [op],
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def set_campaign_status(
    customer_id: str,
    campaign_id: str,
    status: str,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Pauses, enables, or removes a campaign.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The numeric id of the campaign.
        status: ENABLED, PAUSED, or REMOVED. REMOVED is permanent —
            confirm with the user before using it.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    service = client.get_service("CampaignService")
    op = client.get_type("CampaignOperation")
    campaign = op.update
    campaign.resource_name = service.campaign_path(
        utils.clean_customer_id(customer_id), campaign_id
    )
    try:
        campaign.status = client.enums.CampaignStatusEnum[status.upper()]
    except KeyError:
        raise ToolError(
            f"Unknown status '{status}'. Use ENABLED, PAUSED, or REMOVED."
        )
    utils.apply_update_mask(client, op, campaign)
    return utils.mutate(
        "CampaignService",
        "MutateCampaignsRequest",
        "mutate_campaigns",
        customer_id,
        [op],
        validate_only,
    )
