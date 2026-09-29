"""Tools for managing conversion actions (what Smart Bidding optimizes to)."""

from typing import Any, Dict, List

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def set_conversion_action_primary(
    customer_id: str,
    conversion_action_id: str,
    primary: bool,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Marks a conversion action as primary (optimized toward by Smart
    Bidding) or secondary (observed/reported only).

    This is the main lever for making campaigns optimize toward real
    outcomes (e.g. phone calls) instead of soft actions (page views,
    direction clicks). Find ids with `list_conversion_actions`.

    Note: some system-generated conversion actions cannot be edited via
    the API; the error will say so if this one can't.

    Args:
        customer_id: The Google Ads account.
        conversion_action_id: The numeric id of the conversion action.
        primary: True to make it primary, False to demote to secondary.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    service = client.get_service("ConversionActionService")
    op = client.get_type("ConversionActionOperation")
    action = op.update
    action.resource_name = service.conversion_action_path(
        utils.clean_customer_id(customer_id), conversion_action_id
    )
    action.primary_for_goal = primary
    utils.apply_update_mask(client, op, action)
    return utils.mutate(
        "ConversionActionService",
        "MutateConversionActionsRequest",
        "mutate_conversion_actions",
        customer_id,
        [op],
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def set_campaign_conversion_goals(
    customer_id: str,
    campaign_id: str,
    goals: List[Dict[str, Any]],
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Overrides, per campaign, which conversion goals Smart Bidding
    optimizes toward — regardless of the account-level primary/secondary
    settings.

    Use this when account-level conversion actions can't be edited (e.g.
    system-generated "Local actions") but a campaign must optimize only
    to real outcomes such as phone calls. This switches the campaign to
    campaign-level goal configuration and sets each listed goal's
    biddable flag; include every category/origin combination that exists
    in the account, marking the ones to optimize toward biddable=true
    and the rest biddable=false.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The campaign to configure.
        goals: Entries like {"category": "PHONE_CALL_LEAD",
            "origin": "WEBSITE", "biddable": true}. Categories/origins
            are ConversionActionCategoryEnum / ConversionOriginEnum
            names (e.g. PHONE_CALL_LEAD, PAGE_VIEW, CONTACT, ENGAGEMENT,
            GET_DIRECTIONS / WEBSITE, GOOGLE_HOSTED, CALL_FROM_ADS).
        validate_only: If True, only validates the requests.
    """
    client = utils.get_googleads_client()
    cid = utils.clean_customer_id(customer_id)

    # Validate enum names up front for clearer errors.
    for g in goals:
        cat = str(g.get("category", "")).upper()
        org = str(g.get("origin", "")).upper()
        try:
            client.enums.ConversionActionCategoryEnum[cat]
            client.enums.ConversionOriginEnum[org]
        except KeyError as e:
            raise ToolError(f"Unknown category/origin in {g}: {e}")

    # 1. Switch the campaign to campaign-level goal configuration.
    cfg_op = client.get_type("ConversionGoalCampaignConfigOperation")
    cfg = cfg_op.update
    cfg.resource_name = (
        f"customers/{cid}/conversionGoalCampaignConfigs/{campaign_id}"
    )
    cfg.goal_config_level = client.enums.GoalConfigLevelEnum.CAMPAIGN
    utils.apply_update_mask(client, cfg_op, cfg)
    utils.mutate(
        "ConversionGoalCampaignConfigService",
        "MutateConversionGoalCampaignConfigsRequest",
        "mutate_conversion_goal_campaign_configs",
        customer_id,
        [cfg_op],
        validate_only,
    )

    # 2. Set biddability per goal.
    operations = []
    for g in goals:
        cat = str(g["category"]).upper()
        org = str(g["origin"]).upper()
        op = client.get_type("CampaignConversionGoalOperation")
        goal = op.update
        goal.resource_name = (
            f"customers/{cid}/campaignConversionGoals/"
            f"{campaign_id}~{cat}~{org}"
        )
        goal.biddable = bool(g["biddable"])
        utils.apply_update_mask(client, op, goal)
        operations.append(op)
    return utils.mutate(
        "CampaignConversionGoalService",
        "MutateCampaignConversionGoalsRequest",
        "mutate_campaign_conversion_goals",
        customer_id,
        operations,
        validate_only,
    )
