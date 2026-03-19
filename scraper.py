"""
core/scraper.py — Indeed job scraper using the Indeed MCP API pattern.

Builds search queries from current criteria, hits Indeed, filters results,
and returns clean job dicts ready to upsert into the state DB.
"""

import os
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

INDEED_API_KEY  = os.environ.get("INDEED_API_KEY", "")
RAPID_API_KEY   = os.environ.get("RAPID_API_KEY", "")   # fallback via RapidAPI

# ── 25-mile radius expansion map ────────────────────────────────────────────
RADIUS_MAP = {
    "sayreville, nj": [
        "Woodbridge, NJ", "Rahway, NJ", "Linden, NJ", "Elizabeth, NJ",
        "Newark, NJ", "Perth Amboy, NJ", "Metuchen, NJ",
        "New Brunswick, NJ", "Edison, NJ", "Piscataway, NJ",
        "New York, NY",
    ],
    "new york, ny": ["New York, NY", "Brooklyn, NY", "Jersey City, NJ"],
}

# ── Title queries by tier ────────────────────────────────────────────────────
TIER_QUERIES = {
    "manager": [
        "Operations Manager",
        "Branch Operations Manager",
        "General Manager Operations",
        "Senior Operations Manager",
        "Director of Operations",
        "Head of Operations",
    ],
    "director": [
        "Director of Operations",
        "Head of Operations",
        "Director Business Operations",
        "VP of Operations",
        "Senior Director Operations",
        "Operations Director high growth",
        "Director Operations trades services",
    ],
    "executive": [
        "COO",
        "Chief Operating Officer",
        "VP of Operations",
        "SVP Operations",
        "President of Operations",
    ],
}

# Specialty queries always added
SPECIALTY_QUERIES = [
    "Director Operations services company",
    "Operations Director startup",
]


def expand_location(base_location: str) -> list[str]:
    """Return list of search location strings for a given base location."""
    key = base_location.lower().strip()
    if key in RADIUS_MAP:
        return RADIUS_MAP[key]
    # Generic fallback: just use the location itself
    return [base_location]


def build_search_matrix(criteria: dict) -> list[tuple[str, str]]:
    """Return list of (query, location) tuples to search."""
    tier     = criteria.get("title_tier", "director").lower()
    base_loc = criteria.get("base_location", "Sayreville, NJ")
    locations = expand_location(base_loc)
    queries   = TIER_QUERIES.get(tier, TIER_QUERIES["director"]) + SPECIALTY_QUERIES
    matrix    = [(q, loc) for q in queries for loc in locations]
    return matrix


def parse_salary_floor(criteria: dict) -> int:
    raw = criteria.get("salary_floor", "80000")
    cleaned = re.sub(r"[^\d]", "", str(raw))
    return int(cleaned) if cleaned else 80000


def salary_meets_floor(salary_str: str, floor: int) -> bool:
    """Check if the listed salary string meets the floor. Returns True if salary not listed."""
    if not salary_str or salary_str.strip().lower() in ("", "not listed", "n/a"):
        return True   # Include jobs without listed salary
    nums = re.findall(r"\d[\d,]*", salary_str.replace(",", ""))
    if not nums:
        return True
    low = int(nums[0])
    return low >= floor


def level_from_title(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["coo", "chief operating", "svp", "senior vp", "president of op"]):
        return "COO"
    if any(x in t for x in ["vp ", "vice president", "v.p."]):
        return "VP"
    if any(x in t for x in ["director", "head of"]):
        return "Director"
    if any(x in t for x in ["manager", "general manager"]):
        return "Manager"
    return "Other"


def search_indeed_rapidapi(query: str, location: str) -> list[dict]:
    """Search Indeed via RapidAPI's JSearch endpoint (free tier available)."""
    if not RAPID_API_KEY:
        logger.warning("RAPID_API_KEY not set — skipping search")
        return []
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    params = {
        "query":     f"{query} in {location}",
        "page":      "1",
        "num_results": "10",
        "date_posted": "month",
        "employment_types": "FULLTIME",
        "country":   "us",
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = []
        for item in data.get("data", []):
            jobs.append({
                "id":          item.get("job_id", ""),
                "title":       item.get("job_title", ""),
                "company":     item.get("employer_name", ""),
                "location":    f"{item.get('job_city','')}, {item.get('job_state','')}".strip(", "),
                "salary":      _extract_salary(item),
                "level":       level_from_title(item.get("job_title", "")),
                "industry":    item.get("employer_company_type", ""),
                "apply_url":   item.get("job_apply_link", ""),
                "date_posted": item.get("job_posted_at_datetime_utc", "")[:10],
                "notes":       "",
            })
        return jobs
    except Exception as e:
        logger.error(f"RapidAPI search error: {e}")
        return []


def _extract_salary(item: dict) -> str:
    """Pull salary string from a JSearch result."""
    min_s = item.get("job_min_salary")
    max_s = item.get("job_max_salary")
    period = item.get("job_salary_period", "")
    if min_s and max_s:
        if period == "YEAR":
            return f"${int(min_s):,} – ${int(max_s):,} a year"
        elif period == "HOUR":
            return f"${min_s:.0f} – ${max_s:.0f} an hour"
        return f"${int(min_s):,} – ${int(max_s):,}"
    return "Not Listed"


def run_full_search(criteria: dict) -> list[dict]:
    """
    Execute the full search matrix and return filtered, deduplicated job list.
    Uses RapidAPI JSearch as the Indeed data source.
    """
    matrix       = build_search_matrix(criteria)
    salary_floor = parse_salary_floor(criteria)
    seen_ids     = set()
    all_jobs     = []

    logger.info(f"Running {len(matrix)} searches (tier={criteria.get('title_tier')}, "
                f"floor=${salary_floor:,}, base={criteria.get('base_location')})")

    for query, location in matrix:
        results = search_indeed_rapidapi(query, location)
        for job in results:
            jid = job.get("id", "")
            if not jid or jid in seen_ids:
                continue
            if not salary_meets_floor(job.get("salary", ""), salary_floor):
                continue
            lvl = job.get("level", "Other")
            if lvl == "Other":
                continue
            seen_ids.add(jid)
            all_jobs.append(job)

    logger.info(f"Search complete: {len(all_jobs)} qualifying jobs found")
    return all_jobs
