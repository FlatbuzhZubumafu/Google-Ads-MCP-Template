"""Tools for creating and updating campaign budgets."""

from typing import Any, Dict

from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def create_campaign_budget(
    customer_id: str,
    name: str,
    daily_amount: float,
    explicitly_shared: bool = False,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Creates a daily campaign budget. Returns its resource name, which
    is required when creating a campaign.

    Args:
        customer_id: The Google Ads account to create the budget in.
        name: A unique budget name.
        daily_amount: Daily budget in the account's currency units
            (e.g. 25.50 means $25.50 for a USD account).
        explicitly_shared: Whether the budget can be shared by multiple
            campaigns (default False).
        validate_only: If True, only validates the request without
            creating anything.
    """
    client = utils.get_googleads_client()
    op = client.get_type("CampaignBudgetOperation")
    budget = op.create
    budget.name = name
    budget.amount_micros = utils.micros(daily_amount)
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget.explicitly_shared = explicitly_shared
    return utils.mutate(
        "CampaignBudgetService",
        "MutateCampaignBudgetsRequest",
        "mutate_campaign_budgets",
        customer_id,
        [op],
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def update_campaign_budget(
    customer_id: str,
    budget_id: str,
    daily_amount: float,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Changes the daily amount of an existing campaign budget.

    Find the budget id via the `search` tool (campaign_budget.id) or from
    a campaign's campaign.campaign_budget resource name.

    Args:
        customer_id: The Google Ads account.
        budget_id: The numeric id of the budget to update.
        daily_amount: New daily budget in the account's currency units.
        validate_only: If True, only validates the request without
            applying it.
    """
    client = utils.get_googleads_client()
    service = client.get_service("CampaignBudgetService")
    op = client.get_type("CampaignBudgetOperation")
    budget = op.update
    budget.resource_name = service.campaign_budget_path(
        utils.clean_customer_id(customer_id), budget_id
    )
    budget.amount_micros = utils.micros(daily_amount)
    utils.apply_update_mask(client, op, budget)
    return utils.mutate(
        "CampaignBudgetService",
        "MutateCampaignBudgetsRequest",
        "mutate_campaign_budgets",
        customer_id,
        [op],
        validate_only,
    )
