"""Tools for discovering accessible Google Ads accounts."""

from typing import Any, Dict, List

from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def list_accessible_customers() -> List[str]:
    """Returns the ids of Google Ads accounts directly accessible by the
    authenticated user.

    Use this tool first to discover available customer IDs if the user
    hasn't provided one. Most other tools require a valid customer ID.

    Returns:
        List[str]: A list of customer IDs (10-digit strings, no dashes).
    """
    ga_service = utils.get_googleads_service("CustomerService")
    response = ga_service.list_accessible_customers()
    return [
        rn.removeprefix("customers/") for rn in response.resource_names
    ]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_account_hierarchy(customer_id: str) -> List[Dict[str, Any]]:
    """Lists all client accounts under a (manager) account, including the
    account itself.

    Useful when the authenticated user works through an MCC/manager
    account: run this against the manager's customer ID to find the child
    account IDs to use with reporting and management tools.

    Args:
        customer_id: The manager (or standalone) account ID, digits only
            or in 123-456-7890 form.
    """
    query = (
        "SELECT customer_client.id, customer_client.descriptive_name, "
        "customer_client.level, customer_client.manager, "
        "customer_client.status, customer_client.currency_code, "
        "customer_client.time_zone "
        "FROM customer_client "
        "WHERE customer_client.level <= 2 "
        "ORDER BY customer_client.level"
    )
    return utils.run_query(customer_id, query)
