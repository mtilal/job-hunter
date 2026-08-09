import requests
import re
from typing import List, Dict

try:
    from jobspy import scrape_jobs as _scrape
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False


def _strip_html(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text or "")
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    return re.sub(r'\s+', ' ', text).strip()


# ── Remotive (remote global) ───────────────────────────────────────────────────
def fetch_remotive(search: str, limit: int = 25) -> List[Dict]:
    try:
        r = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": search, "limit": limit},
            timeout=15,
        )
        r.raise_for_status()
        out = []
        for j in r.json().get("jobs", []):
            out.append({
                "id": f"remotive-{j.get('id')}",
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location") or "Remote",
                "job_type": j.get("job_type", ""),
                "salary": j.get("salary", ""),
                "description": _strip_html(j.get("description", ""))[:3000],
                "url": j.get("url", ""),
                "posted_at": j.get("publication_date", "")[:10],
                "source": "Remotive",
                "region": "International / Remote",
            })
        return out
    except Exception as e:
        return [{"_error": str(e), "source": "Remotive"}]


# ── Arbeitnow (global) ────────────────────────────────────────────────────────
def fetch_arbeitnow(search: str, remote: bool = False, limit: int = 25) -> List[Dict]:
    try:
        params: Dict = {}
        if search:
            params["q"] = search
        if remote:
            params["remote"] = "true"
        r = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        out = []
        for j in r.json().get("data", [])[:limit]:
            out.append({
                "id": f"arbeitnow-{j.get('slug', '')}",
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("location", ""),
                "job_type": (j.get("job_types") or [""])[0],
                "salary": "",
                "description": _strip_html(j.get("description", ""))[:3000],
                "url": j.get("url", ""),
                "posted_at": str(j.get("created_at", ""))[:10],
                "source": "Arbeitnow",
                "region": "International",
            })
        return out
    except Exception as e:
        return [{"_error": str(e), "source": "Arbeitnow"}]


# ── Jobicy (remote) ───────────────────────────────────────────────────────────
def fetch_jobicy(search: str, limit: int = 20) -> List[Dict]:
    try:
        r = requests.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"tag": search, "count": limit},
            timeout=15,
        )
        r.raise_for_status()
        out = []
        for j in r.json().get("jobs", []):
            out.append({
                "id": f"jobicy-{j.get('id')}",
                "title": j.get("jobTitle", ""),
                "company": j.get("companyName", ""),
                "location": j.get("jobGeo") or "Remote",
                "job_type": j.get("jobType", ""),
                "salary": j.get("annualSalaryMin", ""),
                "description": _strip_html(j.get("jobDescription", ""))[:3000],
                "url": j.get("url", ""),
                "posted_at": j.get("pubDate", "")[:10],
                "source": "Jobicy",
                "region": "International / Remote",
            })
        return out
    except Exception as e:
        return [{"_error": str(e), "source": "Jobicy"}]


# ── Adzuna (multi-country, free API key required) ─────────────────────────────
ADZUNA_COUNTRY_MAP = {
    "Pakistan": ("pk", "Pakistan"),
    "United Kingdom": ("gb", "UK"),
    "United States": ("us", "USA"),
    "Germany": ("de", "Germany"),
    "Australia": ("au", "Australia"),
    "Canada": ("ca", "Canada"),
    "UAE": ("ae", "UAE"),
    "Singapore": ("sg", "Singapore"),
}


def fetch_adzuna(
    search: str,
    country: str,
    app_id: str,
    app_key: str,
    location: str = "",
    limit: int = 25,
) -> List[Dict]:
    code, label = ADZUNA_COUNTRY_MAP.get(country, ("us", country))
    params: Dict = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": limit,
        "what": search,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    try:
        r = requests.get(
            f"https://api.adzuna.com/v1/api/jobs/{code}/search/1",
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        out = []
        for j in r.json().get("results", []):
            salary_min = j.get("salary_min", "")
            salary_max = j.get("salary_max", "")
            salary = ""
            if salary_min and salary_max:
                salary = f"{salary_min:,.0f} – {salary_max:,.0f}"
            elif salary_min:
                salary = f"From {salary_min:,.0f}"

            out.append({
                "id": f"adzuna-{j.get('id', '')}",
                "title": j.get("title", ""),
                "company": (j.get("company") or {}).get("display_name", ""),
                "location": (j.get("location") or {}).get("display_name", label),
                "job_type": j.get("contract_time", ""),
                "salary": salary,
                "description": _strip_html(j.get("description", ""))[:3000],
                "url": j.get("redirect_url", ""),
                "posted_at": (j.get("created") or "")[:10],
                "source": f"Adzuna ({label})",
                "region": "Local" if country == "Pakistan" else "International",
            })
        return out
    except Exception as e:
        return [{"_error": str(e), "source": f"Adzuna ({country})"}]


# ── Countries supported for Indeed/LinkedIn search ───────────────────────────
# Display name → value jobspy expects.
_COUNTRY_OVERRIDES = {
    "USA": "United States",
    "UK": "United Kingdom",
    "UNITEDARABEMIRATES": "United Arab Emirates",
    "SOUTHAFRICA": "South Africa",
    "SOUTHKOREA": "South Korea",
    "NEWZEALAND": "New Zealand",
    "HONGKONG": "Hong Kong",
    "CZECHREPUBLIC": "Czech Republic",
    "COSTARICA": "Costa Rica",
    "SAUDIARABIA": "Saudi Arabia",
    "US_CANADA": "US & Canada",
    "WORLDWIDE": "Worldwide",
}


def _build_country_map() -> Dict[str, str]:
    if not JOBSPY_AVAILABLE:
        return {"Worldwide": "worldwide"}
    from jobspy.model import Country
    out = {}
    for c in Country:
        display = _COUNTRY_OVERRIDES.get(c.name, c.name.capitalize())
        out[display] = c.name.lower()
    return dict(sorted(out.items()))


COUNTRIES = _build_country_map()

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship", "Temporary"]
WORKPLACE_TYPES = ["Remote", "On-site", "Hybrid"]

_TYPE_ALIASES = {
    "fulltime": "Full-time", "full_time": "Full-time", "full time": "Full-time",
    "permanent": "Full-time",
    "parttime": "Part-time", "part_time": "Part-time", "part time": "Part-time",
    "contract": "Contract", "contractor": "Contract", "freelance": "Contract",
    "internship": "Internship", "intern": "Internship",
    "temporary": "Temporary", "temp": "Temporary",
}


def normalize_job_type(job: Dict) -> str:
    """Map the many raw job_type spellings onto one of JOB_TYPES."""
    raw = str(job.get("job_type") or "").strip().lower().replace("-", "")
    for alias, label in _TYPE_ALIASES.items():
        if alias.replace("-", "").replace("_", "").replace(" ", "") in raw.replace("_", "").replace(" ", ""):
            return label
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    for alias, label in _TYPE_ALIASES.items():
        if alias in text:
            return label
    return ""


def infer_workplace(job: Dict) -> str:
    """Best-effort Remote / Hybrid / On-site classification."""
    blob = " ".join([
        str(job.get("location") or ""),
        str(job.get("title") or ""),
        str(job.get("description") or "")[:600],
    ]).lower()
    if "hybrid" in blob:
        return "Hybrid"
    if "remote" in blob or "work from home" in blob or "wfh" in blob:
        return "Remote"
    if "on-site" in blob or "onsite" in blob or "in office" in blob or "in-person" in blob:
        return "On-site"
    return "On-site" if job.get("location") else ""


def _text_val(value) -> str:
    """
    pandas uses NaN for empty cells, and NaN is truthy — so a plain str() turns
    a missing field into the literal string "nan". Normalise those to "".
    """
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("nan", "none", "nat", "<na>") else text


def _num_val(value):
    """Return a float, or None when the cell is missing/NaN."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return None if num != num else num  # NaN is the only value unequal to itself


def _format_salary(row) -> str:
    lo = _num_val(row.get("min_amount"))
    hi = _num_val(row.get("max_amount"))
    if lo is None and hi is None:
        return ""

    currency = _text_val(row.get("currency"))
    interval = _text_val(row.get("interval")) or _text_val(row.get("salary_source"))
    suffix = f" / {interval}" if interval else ""
    prefix = f"{currency} " if currency else ""

    if lo is not None and hi is not None:
        return f"{prefix}{lo:,.0f} – {hi:,.0f}{suffix}"
    amount = lo if lo is not None else hi
    return f"{prefix}{amount:,.0f}+{suffix}"


# ── Indeed + LinkedIn via jobspy ─────────────────────────────────────────────
def fetch_jobspy(
    search: str,
    sites: List[str],
    location: str = "",
    results: int = 20,
    country: str = "USA",
    is_remote: bool = False,
) -> List[Dict]:
    if not JOBSPY_AVAILABLE:
        return [{"_error": "jobspy not installed in this Python environment.", "source": ", ".join(sites)}]
    try:
        df = _scrape(
            site_name=sites,
            search_term=search,
            location=location or country,
            results_wanted=results,
            country_indeed=COUNTRIES.get(country, "usa"),
            is_remote=is_remote,
            verbose=0,
        )
        out = []
        for _, row in df.iterrows():
            site = _text_val(row.get("site")).capitalize()
            region = "Local" if country.lower() in ("pk", "pakistan") else "International"
            out.append({
                "id": f"jobspy-{site}-{_text_val(row.get('id'))}",
                "title": _text_val(row.get("title")),
                "company": _text_val(row.get("company")),
                "location": _text_val(row.get("location")),
                "job_type": _text_val(row.get("job_type")),
                "salary": _format_salary(row),
                "description": _strip_html(_text_val(row.get("description")))[:3000],
                "url": _text_val(row.get("job_url")),
                "posted_at": _text_val(row.get("date_posted"))[:10],
                "source": site,
                "region": region,
            })
        return out
    except Exception as e:
        return [{"_error": str(e), "source": ", ".join(sites)}]


# ── Visa sponsorship post-filter ──────────────────────────────────────────────
VISA_KEYWORDS = [
    "visa sponsor", "visa sponsorship", "sponsorship provided",
    "will sponsor", "work authorization", "work permit",
    "relocation", "relocation package", "h1b", "tier 2", "skilled worker visa",
    "global talent", "international candidates welcome",
]


def has_visa_sponsorship(job: Dict) -> bool:
    text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
    return any(kw in text for kw in VISA_KEYWORDS)
