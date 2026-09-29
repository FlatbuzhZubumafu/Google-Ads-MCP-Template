"""Canned performance reports for routine (e.g. weekly) account monitoring.

These wrap common GAQL queries so a model can pull the usual health
metrics without composing queries by hand. For anything not covered
here, use the generic `search` tool.
"""

import datetime
from typing import Any, Dict, List

from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.coordinator import mcp

_PREDEFINED_RANGES = {
    "TODAY",
    "YESTERDAY",
    "LAST_7_DAYS",
    "LAST_14_DAYS",
    "LAST_30_DAYS",
    "LAST_BUSINESS_WEEK",
    "LAST_WEEK_SUN_SAT",
    "LAST_WEEK_MON_SUN",
    "THIS_WEEK_SUN_TODAY",
    "THIS_WEEK_MON_TODAY",
    "THIS_MONTH",
    "LAST_MONTH",
}

_CORE_METRICS = (
    "metrics.impressions, metrics.clicks, metrics.ctr, "
    "metrics.average_cpc, metrics.cost_micros, metrics.conversions, "
    "metrics.conversions_value, metrics.cost_per_conversion"
)


def _date_clause(
    date_range: str, start_date: str | None, end_date: str | None
) -> str:
    """Builds the segments.date WHERE clause for a report."""
    if start_date or end_date:
        if not (start_date and end_date):
            raise ToolError(
                "Provide both start_date and end_date (YYYY-MM-DD), "
                "or neither."
            )
        return (
            f"segments.date BETWEEN '{start_date}' AND '{end_date}'"
        )
    range_name = date_range.upper().strip()
    if range_name not in _PREDEFINED_RANGES:
        raise ToolError(
            f"Unknown date_range '{date_range}'. Use one of: "
            f"{sorted(_PREDEFINED_RANGES)} or pass start_date/end_date."
        )
    return f"segments.date DURING {range_name}"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_campaign_performance(
    customer_id: str,
    date_range: str = "LAST_7_DAYS",
    start_date: str | None = None,
    end_date: str | None = None,
    include_removed: bool = False,
) -> List[Dict[str, Any]]:
    """Campaign-level performance report: impressions, clicks, CTR, cost,
    conversions, conversion value, plus campaign status, bidding strategy
    and daily budget. Ordered by cost, highest first.

    Cost and budget fields are in micros: divide by 1,000,000 for the
    account currency amount.

    Args:
        customer_id: The Google Ads account to report on.
        date_range: A predefined range such as LAST_7_DAYS, LAST_14_DAYS,
            LAST_30_DAYS, LAST_MONTH, THIS_MONTH. Ignored when
            start_date/end_date are given.
        start_date: Optional custom range start (YYYY-MM-DD).
        end_date: Optional custom range end (YYYY-MM-DD).
        include_removed: Include removed campaigns (default False).
    """
    where = [_date_clause(date_range, start_date, end_date)]
    if not include_removed:
        where.append("campaign.status != 'REMOVED'")
    query = (
        "SELECT campaign.id, campaign.name, campaign.status, "
        "campaign.advertising_channel_type, campaign.bidding_strategy_type, "
        "campaign_budget.amount_micros, "
        f"{_CORE_METRICS}, metrics.search_impression_share "
        "FROM campaign "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY metrics.cost_micros DESC"
    )
    return utils.run_query(customer_id, query)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_ad_group_performance(
    customer_id: str,
    campaign_id: str | None = None,
    date_range: str = "LAST_7_DAYS",
    start_date: str | None = None,
    end_date: str | None = None,
) -> List[Dict[str, Any]]:
    """Ad-group-level performance report with the core metrics
    (impressions, clicks, CTR, cost, conversions). Ordered by cost.

    Args:
        customer_id: The Google Ads account to report on.
        campaign_id: Optionally restrict to a single campaign.
        date_range: Predefined range (see get_campaign_performance).
        start_date: Optional custom range start (YYYY-MM-DD).
        end_date: Optional custom range end (YYYY-MM-DD).
    """
    where = [
        _date_clause(date_range, start_date, end_date),
        "ad_group.status != 'REMOVED'",
    ]
    if campaign_id:
        where.append(f"campaign.id = {int(campaign_id)}")
    query = (
        "SELECT campaign.id, campaign.name, ad_group.id, ad_group.name, "
        f"ad_group.status, {_CORE_METRICS} "
        "FROM ad_group "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY metrics.cost_micros DESC"
    )
    return utils.run_query(customer_id, query)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_keyword_performance(
    customer_id: str,
    campaign_id: str | None = None,
    date_range: str = "LAST_7_DAYS",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Keyword-level performance report: keyword text, match type, status,
    quality score, and the core metrics. Ordered by cost, highest first.

    Args:
        customer_id: The Google Ads account to report on.
        campaign_id: Optionally restrict to a single campaign.
        date_range: Predefined range (see get_campaign_performance).
        start_date: Optional custom range start (YYYY-MM-DD).
        end_date: Optional custom range end (YYYY-MM-DD).
        limit: Max rows to return (default 200).
    """
    where = [
        _date_clause(date_range, start_date, end_date),
        "ad_group_criterion.status != 'REMOVED'",
    ]
    if campaign_id:
        where.append(f"campaign.id = {int(campaign_id)}")
    query = (
        "SELECT campaign.name, ad_group.name, "
        "ad_group_criterion.criterion_id, "
        "ad_group_criterion.keyword.text, "
        "ad_group_criterion.keyword.match_type, "
        "ad_group_criterion.status, "
        "ad_group_criterion.quality_info.quality_score, "
        f"{_CORE_METRICS} "
        "FROM keyword_view "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY metrics.cost_micros DESC "
        f"LIMIT {int(limit)}"
    )
    return utils.run_query(customer_id, query)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_search_terms_report(
    customer_id: str,
    campaign_id: str | None = None,
    date_range: str = "LAST_7_DAYS",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Search terms report: the actual user queries that triggered ads,
    with the core metrics. The main input for finding negative keyword
    candidates and new keyword opportunities. Ordered by cost.

    Args:
        customer_id: The Google Ads account to report on.
        campaign_id: Optionally restrict to a single campaign.
        date_range: Predefined range (see get_campaign_performance).
        start_date: Optional custom range start (YYYY-MM-DD).
        end_date: Optional custom range end (YYYY-MM-DD).
        limit: Max rows to return (default 200).
    """
    where = [_date_clause(date_range, start_date, end_date)]
    if campaign_id:
        where.append(f"campaign.id = {int(campaign_id)}")
    query = (
        "SELECT campaign.name, ad_group.name, "
        "search_term_view.search_term, search_term_view.status, "
        f"{_CORE_METRICS} "
        "FROM search_term_view "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY metrics.cost_micros DESC "
        f"LIMIT {int(limit)}"
    )
    return utils.run_query(customer_id, query)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def get_change_history(
    customer_id: str,
    days_back: int = 14,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Recent changes made to the account (by users, tools, or this
    server): what changed, when, and by whom. Useful for a weekly
    review of account activity.

    Args:
        customer_id: The Google Ads account to inspect.
        days_back: How many days of history to fetch (max 29 — the API
            only keeps change events for ~30 days).
        limit: Max events to return (API requires a LIMIT <= 10000).
    """
    days_back = min(int(days_back), 29)
    limit = min(int(limit), 10000)
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days_back)
    query = (
        "SELECT change_event.change_date_time, "
        "change_event.change_resource_type, "
        "change_event.resource_change_operation, "
        "change_event.changed_fields, change_event.user_email, "
        "change_event.client_type, change_event.campaign, "
        "change_event.ad_group "
        "FROM change_event "
        f"WHERE change_event.change_date_time >= '{start:%Y-%m-%d}' "
        f"AND change_event.change_date_time <= '{end + datetime.timedelta(days=1):%Y-%m-%d}' "
        "ORDER BY change_event.change_date_time DESC "
        f"LIMIT {limit}"
    )
    return utils.run_query(customer_id, query)
