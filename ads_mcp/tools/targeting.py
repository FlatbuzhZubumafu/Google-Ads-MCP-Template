"""Tools for campaign targeting: locations and ad schedules."""

from typing import Any, Dict, List

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp

_DAYS = (
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
)


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def add_location_targeting(
    customer_id: str,
    campaign_id: str,
    geo_target_ids: List[str],
    negative: bool = False,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Adds location targeting criteria to a campaign.

    Resolve human-readable places to ids first with `suggest_geo_targets`.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The campaign to target.
        geo_target_ids: Numeric geo target constant ids (e.g. 1013962).
        negative: If True, EXCLUDE these locations instead.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    campaign_path = client.get_service("CampaignService").campaign_path(
        utils.clean_customer_id(customer_id), campaign_id
    )
    operations = []
    for geo_id in geo_target_ids:
        op = client.get_type("CampaignCriterionOperation")
        criterion = op.create
        criterion.campaign = campaign_path
        criterion.negative = negative
        criterion.location.geo_target_constant = (
            f"geoTargetConstants/{int(geo_id)}"
        )
        operations.append(op)
    return utils.mutate(
        "CampaignCriterionService",
        "MutateCampaignCriteriaRequest",
        "mutate_campaign_criteria",
        customer_id,
        operations,
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
def remove_campaign_criterion(
    customer_id: str,
    campaign_id: str,
    criterion_id: str,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Removes a single targeting criterion (e.g. a wrong location or an
    obsolete ad schedule) from a campaign.

    Find criterion ids with `list_campaign_criteria`. Removing a criterion
    only changes targeting; it does not touch ads, keywords, or budgets.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The campaign the criterion belongs to.
        criterion_id: The criterion to remove.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    service = client.get_service("CampaignCriterionService")
    op = client.get_type("CampaignCriterionOperation")
    op.remove = service.campaign_criterion_path(
        utils.clean_customer_id(customer_id), campaign_id, criterion_id
    )
    return utils.mutate(
        "CampaignCriterionService",
        "MutateCampaignCriteriaRequest",
        "mutate_campaign_criteria",
        customer_id,
        [op],
        validate_only,
    )


@mcp.tool(annotations=ToolAnnotations(destructiveHint=False))
def set_ad_schedule(
    customer_id: str,
    campaign_id: str,
    schedule: List[Dict[str, Any]],
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Adds ad schedule criteria to a campaign (which days/hours ads run).

    A campaign with no ad schedule runs 24/7. Once any schedule entries
    exist, ads run ONLY during the scheduled windows — so include every
    window you want covered. Hours are in the account's time zone.

    Args:
        customer_id: The Google Ads account.
        campaign_id: The campaign to schedule.
        schedule: Entries like
            {"day": "MONDAY", "start_hour": 8, "end_hour": 18}.
            day is MONDAY..SUNDAY; hours are 0-24.
        validate_only: If True, only validates the request.
    """
    client = utils.get_googleads_client()
    campaign_path = client.get_service("CampaignService").campaign_path(
        utils.clean_customer_id(customer_id), campaign_id
    )
    zero = client.enums.MinuteOfHourEnum.ZERO
    operations = []
    for entry in schedule:
        day = str(entry.get("day", "")).upper()
        if day not in _DAYS:
            raise ToolError(f"Invalid day '{entry.get('day')}'. Use {_DAYS}")
        op = client.get_type("CampaignCriterionOperation")
        criterion = op.create
        criterion.campaign = campaign_path
        criterion.ad_schedule.day_of_week = client.enums.DayOfWeekEnum[day]
        criterion.ad_schedule.start_hour = int(entry["start_hour"])
        criterion.ad_schedule.end_hour = int(entry["end_hour"])
        criterion.ad_schedule.start_minute = zero
        criterion.ad_schedule.end_minute = zero
        operations.append(op)
    return utils.mutate(
        "CampaignCriterionService",
        "MutateCampaignCriteriaRequest",
        "mutate_campaign_criteria",
        customer_id,
        operations,
        validate_only,
    )
