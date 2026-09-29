"""Tools for assets — currently call assets (phone numbers on ads)."""

from typing import Any, Dict

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def create_call_asset(
    customer_id: str,
    phone_number: str,
    country_code: str = "US",
    call_conversion_action_id: str | None = None,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Creates a call asset (clickable phone number shown with ads).
    Returns its resource name; attach it to a campaign with
    `link_asset_to_campaign`.

    Args:
        customer_id: The Google Ads account.
        phone_number: The business phone number, e.g. "(480) 555-0100".
        country_code: Two-letter country code of the number.
        call_conversion_action_id: Optional conversion action to count
            calls from this asset against (e.g. a "Calls from ads"
            action). If omitted, the account-level setting is used.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    op = client.get_type("AssetOperation")
    asset = op.create
    asset.call_asset.country_code = country_code
    asset.call_asset.phone_number = phone_number
    if call_conversion_action_id:
        asset.call_asset.call_conversion_reporting_state = (
            client.enums.CallConversionReportingStateEnum.USE_RESOURCE_LEVEL_CALL_CONVERSION_ACTION
        )
        asset.call_asset.call_conversion_action = client.get_service(
            "ConversionActionService"
        ).conversion_action_path(
            utils.clean_customer_id(customer_id), call_conversion_action_id
        )
    else:
        asset.call_asset.call_conversion_reporting_state = (
            client.enums.CallConversionReportingStateEnum.USE_ACCOUNT_LEVEL_CALL_CONVERSION_ACTION
        )
    return utils.mutate(
        "AssetService",
        "MutateAssetsRequest",
        "mutate_assets",
        customer_id,
        [op],
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def link_asset_to_campaign(
    customer_id: str,
    campaign_id: str,
    asset_resource_name: str,
    field_type: str = "CALL",
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Links an asset (e.g. a call asset) to a campaign so it serves with
    that campaign's ads.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The campaign to attach the asset to.
        asset_resource_name: Resource name returned by create_call_asset
            (customers/123/assets/456).
        field_type: The asset's role, e.g. CALL or SITELINK.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    try:
        field_enum = client.enums.AssetFieldTypeEnum[field_type.upper()]
    except KeyError:
        raise ToolError(f"Unknown field_type '{field_type}'.")
    op = client.get_type("CampaignAssetOperation")
    link = op.create
    link.campaign = client.get_service("CampaignService").campaign_path(
        utils.clean_customer_id(customer_id), campaign_id
    )
    link.asset = asset_resource_name
    link.field_type = field_enum
    return utils.mutate(
        "CampaignAssetService",
        "MutateCampaignAssetsRequest",
        "mutate_campaign_assets",
        customer_id,
        [op],
        validate_only,
    )
