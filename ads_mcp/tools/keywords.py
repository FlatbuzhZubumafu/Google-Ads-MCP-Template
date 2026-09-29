"""Tools for managing keywords and negative keywords."""

from typing import Any, Dict, List

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp

_MATCH_TYPES = ("EXACT", "PHRASE", "BROAD")


def _match_type(client, match_type: str):
    try:
        return client.enums.KeywordMatchTypeEnum[match_type.upper()]
    except KeyError:
        raise ToolError(
            f"Unknown match_type '{match_type}'. Use one of: {_MATCH_TYPES}"
        )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def add_keywords(
    customer_id: str,
    ad_group_id: str,
    keywords: List[str],
    match_type: str = "PHRASE",
    cpc_bid: float | None = None,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Adds keywords to an ad group (ENABLED).

    Args:
        customer_id: The Google Ads account.
        ad_group_id: The numeric id of the ad group.
        keywords: Keyword texts to add (plain text, no match-type
            punctuation — match type is set separately).
        match_type: EXACT, PHRASE, or BROAD (applied to all keywords in
            this call; call again for a different match type).
        cpc_bid: Optional max CPC bid in currency units for these
            keywords.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    ad_group_service = client.get_service("AdGroupService")
    ad_group_path = ad_group_service.ad_group_path(
        utils.clean_customer_id(customer_id), ad_group_id
    )
    match_enum = _match_type(client, match_type)

    operations = []
    for text in keywords:
        op = client.get_type("AdGroupCriterionOperation")
        criterion = op.create
        criterion.ad_group = ad_group_path
        criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        criterion.keyword.text = text
        criterion.keyword.match_type = match_enum
        if cpc_bid:
            criterion.cpc_bid_micros = utils.micros(cpc_bid)
        operations.append(op)

    return utils.mutate(
        "AdGroupCriterionService",
        "MutateAdGroupCriteriaRequest",
        "mutate_ad_group_criteria",
        customer_id,
        operations,
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def set_keyword_status(
    customer_id: str,
    ad_group_id: str,
    criterion_id: str,
    status: str,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Pauses, enables, or removes a keyword.

    Find criterion ids with `get_keyword_performance`
    (ad_group_criterion.criterion_id).

    Args:
        customer_id: The Google Ads account.
        ad_group_id: The numeric id of the ad group containing the keyword.
        criterion_id: The keyword's criterion id.
        status: ENABLED, PAUSED, or REMOVED. REMOVED is permanent —
            confirm with the user before using it.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    service = client.get_service("AdGroupCriterionService")
    op = client.get_type("AdGroupCriterionOperation")
    criterion = op.update
    criterion.resource_name = service.ad_group_criterion_path(
        utils.clean_customer_id(customer_id), ad_group_id, criterion_id
    )
    try:
        criterion.status = client.enums.AdGroupCriterionStatusEnum[
            status.upper()
        ]
    except KeyError:
        raise ToolError(
            f"Unknown status '{status}'. Use ENABLED, PAUSED, or REMOVED."
        )
    utils.apply_update_mask(client, op, criterion)
    return utils.mutate(
        "AdGroupCriterionService",
        "MutateAdGroupCriteriaRequest",
        "mutate_ad_group_criteria",
        customer_id,
        [op],
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def add_negative_keywords(
    customer_id: str,
    campaign_id: str,
    keywords: List[str],
    match_type: str = "PHRASE",
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Adds campaign-level negative keywords, preventing ads from showing
    on those queries. The usual follow-up to reviewing
    `get_search_terms_report`.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The numeric id of the campaign.
        keywords: Keyword texts to exclude.
        match_type: EXACT, PHRASE, or BROAD (applied to all keywords in
            this call).
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    campaign_service = client.get_service("CampaignService")
    campaign_path = campaign_service.campaign_path(
        utils.clean_customer_id(customer_id), campaign_id
    )
    match_enum = _match_type(client, match_type)

    operations = []
    for text in keywords:
        op = client.get_type("CampaignCriterionOperation")
        criterion = op.create
        criterion.campaign = campaign_path
        criterion.negative = True
        criterion.keyword.text = text
        criterion.keyword.match_type = match_enum
        operations.append(op)

    return utils.mutate(
        "CampaignCriterionService",
        "MutateCampaignCriteriaRequest",
        "mutate_campaign_criteria",
        customer_id,
        operations,
        validate_only,
    )
