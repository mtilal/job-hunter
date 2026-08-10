import csv
import io
import textwrap
from datetime import datetime

import streamlit as st

import ui
from job_sources import (
    fetch_remotive, fetch_arbeitnow, fetch_jobicy,
    fetch_adzuna, fetch_jobspy, has_visa_sponsorship,
    normalize_job_type, infer_workplace,
    ADZUNA_COUNTRY_MAP, COUNTRIES, JOB_TYPES, WORKPLACE_TYPES, JOBSPY_AVAILABLE,
)
from scorer import score_jobs, build_profile
from cv_parser import extract_cv_text, guess_name, suggest_keywords

st.set_page_config(
    page_title="Attuned",
    page_icon="◍",
    layout="wide",
    initial_sidebar_state="expanded",
)


def html(markup: str) -> None:
    """Markdown treats four-space-indented blocks as code, so always dedent."""
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


html(ui.styles())

# ── Session state ─────────────────────────────────────────────────────────────
state = st.session_state
state.setdefault("jobs", [])
state.setdefault("saved", set())
state.setdefault("dismissed", set())
state.setdefault("errors", [])
state.setdefault("last_run", "")
state.setdefault("cv_text", "")


# ══════════════════════════════════════════════════════════════════════════════
#  RAIL  (left pane)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # ── Search — always visible, pinned to the top
    html('<div class="rail-label">Search</div>')
    keywords_raw = st.text_input(
        "Job titles", label_visibility="collapsed",
        value=state.get("kw_default", "Project Manager, Data Analyst"),
        placeholder="Job titles, comma-separated",
    )
    search_btn = st.button("Search", use_container_width=True)

    # ── Your profile
    cv_text = state.get("cv_text", "")
    profile = build_profile(cv_text) if cv_text else {}
    cv_summary = state.get("cv_filename", "") if cv_text else "None"

    with st.expander(f"YOUR PROFILE  ·  {cv_summary[:22]}", expanded=not cv_text):
        st.caption("Upload a CV to enable relevance scoring. You can still search without one.")
        uploaded = st.file_uploader(
            "cv", label_visibility="collapsed",
            type=["pdf", "docx", "doc", "md", "markdown", "txt"],
        )
        if uploaded is not None and state.get("cv_filename") != uploaded.name:
            text, err = extract_cv_text(uploaded.name, uploaded.getvalue())
            state.update(cv_text=text, cv_filename=uploaded.name, cv_error=err)
            if text:
                state["kw_default"] = ", ".join(suggest_keywords(text))
            st.rerun()

        if cv_text:
            name = guess_name(cv_text)
            html(f'<div style="font-size:12.5px;color:{ui.INK};margin-top:4px">'
                 f'{ui.icon("file", 13)} <strong>{ui.esc(name or state.get("cv_filename"))}</strong> '
                 f'{ui.chip(f"{len(profile)} skills found", "teal")}</div>')
        if state.get("cv_error"):
            st.warning(state["cv_error"], icon="⚠️")

    # ── Your skills
    if profile:
        ranked = [t.title() for t, _ in sorted(profile.items(), key=lambda x: x[1], reverse=True)]
        with st.expander(f"YOUR SKILLS  ·  {len(ranked)}"):
            active_skills = st.multiselect(
                "Skills used for scoring", options=ranked, default=ranked,
                label_visibility="collapsed",
            )
    else:
        active_skills = []

    # ── Job sites
    source_options = (["Indeed", "LinkedIn"] if JOBSPY_AVAILABLE else []) + \
                     ["Remotive", "Arbeitnow", "Jobicy"]
    with st.expander("JOB SITES  ·  3", expanded=True):
        sources = st.multiselect(
            "Sites", options=source_options, label_visibility="collapsed",
            default=[s for s in ("Indeed", "LinkedIn", "Remotive") if s in source_options],
            placeholder="Choose sites",
        )

    # ── Location
    with st.expander("LOCATION", expanded=True):
        city = st.text_input("City or area", placeholder="Optional")

    # ── Countries
    with st.expander(f"COUNTRIES  ·  {len(state.get('countries_sel', ['Pakistan','United Kingdom','United States']))}"):
        countries = st.multiselect(
            "Countries", options=list(COUNTRIES.keys()), label_visibility="collapsed",
            default=["Pakistan", "United Kingdom", "United States"],
        )
        state["countries_sel"] = countries

    # ── Job type
    with st.expander("JOB TYPE"):
        job_types = st.multiselect("Type", options=JOB_TYPES,
                                   label_visibility="collapsed", placeholder="Any")

    # ── Workplace
    with st.expander("WORKPLACE"):
        workplaces = st.multiselect("Workplace", options=WORKPLACE_TYPES,
                                    label_visibility="collapsed", placeholder="Any")
        visa_only = st.checkbox("Visa sponsorship only")

    # ── Relevance / volume
    with st.expander("RELEVANCE & VOLUME"):
        min_score = st.slider("Minimum relevance", 0, 100, 0, step=5)
        max_per_source = st.slider("Results per site", 5, 50, 20, step=5)

    # ── Adzuna
    with st.expander("ADZUNA"):
        try:
            _sec_id = st.secrets.get("ADZUNA_APP_ID", "")
            _sec_key = st.secrets.get("ADZUNA_APP_KEY", "")
        except Exception:
            _sec_id = _sec_key = ""
        adzuna_on = st.checkbox("Enable Adzuna")
        adzuna_id = st.text_input("App ID", value=_sec_id, disabled=not adzuna_on)
        adzuna_key = st.text_input("App key", value=_sec_key, type="password", disabled=not adzuna_on)
        adzuna_countries = st.multiselect(
            "Markets", options=list(ADZUNA_COUNTRY_MAP.keys()),
            default=["Pakistan", "United Kingdom", "UAE"], disabled=not adzuna_on,
        )

    # ── Rail footer
    active_filters = sum([
        bool(job_types), bool(workplaces), bool(visa_only),
        min_score > 0, bool(city),
    ])
    html(f'<div class="rail-foot"><span class="dot"></span>'
         f'{active_filters} filter{"" if active_filters == 1 else "s"} active</div>')


# ══════════════════════════════════════════════════════════════════════════════
#  SEARCH
# ══════════════════════════════════════════════════════════════════════════════
if search_btn:
    keyword_list = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    if not keyword_list:
        st.warning("Enter at least one job title.")
        st.stop()
    if not sources and not (adzuna_on and adzuna_id and adzuna_key):
        st.warning("Choose at least one job site.")
        st.stop()

    jobspy_sites = [s.lower() for s in sources if s in ("Indeed", "LinkedIn")]
    tasks = []
    for kw in keyword_list:
        for s in sources:
            if s in ("Remotive", "Arbeitnow", "Jobicy"):
                tasks.append((kw, s, None))
        if jobspy_sites:
            for c in (countries or ["United States"]):
                tasks.append((kw, "JobSpy", c))
        if adzuna_on and adzuna_id and adzuna_key:
            for c in adzuna_countries:
                tasks.append((kw, "Adzuna", c))

    all_jobs, errors = [], []
    bar = st.progress(0.0, text="Fetching")
    remote_wanted = workplaces == ["Remote"]

    for i, (kw, src, country) in enumerate(tasks, start=1):
        label = f"{src} · {country}" if country else src
        bar.progress(i / len(tasks), text=f"Fetching {kw} from {label}")

        if src == "Remotive":
            res = fetch_remotive(kw, limit=max_per_source)
        elif src == "Arbeitnow":
            res = fetch_arbeitnow(kw, remote=remote_wanted, limit=max_per_source)
        elif src == "Jobicy":
            res = fetch_jobicy(kw, limit=max_per_source)
        elif src == "JobSpy":
            res = fetch_jobspy(kw, sites=jobspy_sites, location=city,
                               results=max_per_source, country=country,
                               is_remote=remote_wanted)
        else:
            res = fetch_adzuna(kw, country, adzuna_id, adzuna_key,
                               location=city, limit=max_per_source)

        for r in res:
            (errors if "_error" in r else all_jobs).append(
                f"{label}: {r['_error']}" if "_error" in r else r
            )
    bar.empty()

    seen, unique = set(), []
    for j in all_jobs:
        key = j.get("url") or j.get("id")
        if key and key not in seen:
            seen.add(key)
            unique.append(j)

    for j in unique:
        j["visa_sponsored"] = has_visa_sponsorship(j)
        j["type_norm"] = normalize_job_type(j)
        j["workplace"] = infer_workplace(j)

    # Scoring honours skills the user removed in the rail
    scoring_text = cv_text
    if cv_text and active_skills and len(active_skills) < len(profile):
        keep = {s.lower() for s in active_skills}
        scoring_text = "\n".join(k for k in profile if k in keep)

    unique = score_jobs(unique, scoring_text)

    state["jobs"] = unique
    state["errors"] = errors
    state["last_run"] = datetime.now().strftime("%H:%M")


# ══════════════════════════════════════════════════════════════════════════════
#  RESULTS  (right pane)
# ══════════════════════════════════════════════════════════════════════════════
jobs = state["jobs"]

visible = [j for j in jobs if (j.get("url") or j.get("id")) not in state["dismissed"]]
if visa_only:
    visible = [j for j in visible if j.get("visa_sponsored")]
if job_types:
    visible = [j for j in visible if j.get("type_norm") in job_types]
if workplaces:
    visible = [j for j in visible if j.get("workplace") in workplaces]
visible = [j for j in visible if j.get("score", 0) >= min_score]

counts = {"excellent": 0, "good": 0, "low": 0}
for j in visible:
    counts[ui.band(j.get("score", 0))] += 1

# ── Header bar
html(f"""
<div class="appbar">
  <div class="brand">
    {ui.equalizer(counts['excellent'], counts['good'], counts['low'],
                  f"{counts['excellent']} excellent, {counts['good']} good, {counts['low']} low")}
    <span class="brand-name">ATTUNE<span class="d">D</span></span>
  </div>
  <span class="tagline">Roles that match what you actually do</span>
  <span class="appbar-right">{'Last run ' + state['last_run'] if state['last_run'] else 'Not run yet'}</span>
</div>
""")

if state["errors"]:
    with st.expander(f"{len(state['errors'])} source error(s)"):
        for e in state["errors"]:
            st.caption(e)

if not jobs:
    html(f"""
    <div class="empty">
      <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden="true">
        <rect x="8" y="30" width="8" height="18" rx="4" fill="{ui.TEAL}" opacity=".85"/>
        <rect x="24" y="18" width="8" height="30" rx="4" fill="{ui.ULTRAMARINE}" opacity=".85"/>
        <rect x="40" y="26" width="8" height="22" rx="4" fill="{ui.SLATE}" opacity=".55"/>
      </svg>
      <h3>No results yet</h3>
      <p>Upload your CV, set your job titles in the rail, then run a search.</p>
    </div>
    """)
    st.stop()

# ── Results header
sort_col, export_col = st.columns([3, 1])
with sort_col:
    sort_by = st.selectbox(
        "Sort", ["Relevance", "Most recent", "Company A–Z", "Lowest score first"],
        label_visibility="collapsed",
    )

filter_col, saved_col = st.columns([3, 1])
with filter_col:
    needle = st.text_input("Filter within results", label_visibility="collapsed",
                           placeholder="Filter within results")
with saved_col:
    saved_only = st.checkbox("Saved only")

if needle:
    n = needle.lower()
    visible = [j for j in visible
               if n in str(j.get("title", "")).lower() or n in str(j.get("company", "")).lower()]
if saved_only:
    visible = [j for j in visible if (j.get("url") or j.get("id")) in state["saved"]]

if sort_by == "Relevance":
    visible.sort(key=lambda x: x.get("score", 0), reverse=True)
elif sort_by == "Most recent":
    visible.sort(key=lambda x: x.get("posted_at", ""), reverse=True)
elif sort_by == "Company A–Z":
    visible.sort(key=lambda x: (x.get("company") or "").lower())
else:
    visible.sort(key=lambda x: x.get("score", 0))

n_sites = len({j.get("source", "") for j in visible})
html(f"""
<div class="rhead">
  <span class="rhead-count">{len(visible)} jobs</span>
  <span class="rhead-sub">{n_sites} sites · {len(state['dismissed'])} hidden · {len(state['saved'])} saved</span>
</div>
""")
html(ui.distribution_meter(counts["excellent"], counts["good"], counts["low"]))

with export_col:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Score", "Title", "Company", "Location", "Type", "Workplace",
                     "Salary", "Posted", "Source", "URL"])
    for j in visible:
        writer.writerow([j.get("score", 0), j.get("title", ""), j.get("company", ""),
                         j.get("location", ""), j.get("type_norm", ""), j.get("workplace", ""),
                         j.get("salary", ""), j.get("posted_at", ""), j.get("source", ""),
                         j.get("url", "")])
    st.download_button("Export CSV", buf.getvalue(), "attuned-jobs.csv",
                       "text/csv", use_container_width=True)

# ── Stat strip
if visible:
    scores = [j.get("score", 0) for j in visible]
    cards = [
        (len(visible), "Shown", ui.INK),
        (sum(scores) // len(scores), "Avg match", ui.INK),
        (counts["excellent"], "Excellent", ui.TEAL),
        (counts["good"], "Good", ui.ULTRAMARINE),
        (sum(1 for j in visible if j.get("visa_sponsored")), "Visa", ui.SLATE),
        (sum(1 for j in visible if j.get("workplace") == "Remote"), "Remote", ui.SLATE),
    ]
    for col, (value, label, accent) in zip(st.columns(6, gap="small"), cards):
        with col:
            html(ui.stat_card(value, label, accent))
    st.markdown("")

if not visible:
    culprit = (f"A minimum relevance of {min_score}" if min_score > 0
               else "Your current filters")
    html(f"""
    <div class="empty">
      <h3>Nothing matches</h3>
      <p>{culprit} is excluding all {len(jobs)} fetched jobs.</p>
    </div>
    """)
    st.stop()

# ── Job list
for job in visible:
    key = job.get("url") or job.get("id")
    score = job.get("score", 0)
    band = ui.band(score)
    is_saved = key in state["saved"]

    meta = []
    if job.get("company"):
        meta.append(f'<span>{ui.icon("building")}{ui.esc(job["company"])}</span>')
    if job.get("location"):
        meta.append(f'<span>{ui.icon("pin")}{ui.esc(job["location"])}</span>')
    if job.get("salary"):
        meta.append(f'<span>{ui.icon("wallet")}{ui.esc(job["salary"])}</span>')
    if job.get("posted_at"):
        meta.append(f'<span class="mono">{ui.icon("calendar")}{ui.esc(job["posted_at"])}</span>')

    tags = "".join(ui.chip(ui.esc(m), "teal") for m in job.get("key_matches", [])[:4])
    if job.get("type_norm"):
        tags += ui.chip(ui.esc(job["type_norm"]), "neutral")
    if job.get("workplace"):
        tags += ui.chip(ui.esc(job["workplace"]), "neutral")
    if job.get("visa_sponsored"):
        tags += ui.chip("Visa sponsorship", "blue")
    if job.get("source"):
        tags += ui.chip(ui.esc(job["source"]), "neutral")
    if is_saved:
        tags += ui.chip("Saved", "coral")

    html(f"""
    <div class="job {band}">
      <div class="job-row">
        {ui.score_ring(score)}
        <div style="flex:1;min-width:0">
          <p class="job-title"><a href="{ui.esc(job.get('url'))}" target="_blank">{ui.esc(job.get('title'))}</a></p>
          <div class="job-meta">{"".join(meta)}</div>
          <div>{tags}</div>
        </div>
      </div>
    </div>
    """)

    with st.expander("Description & apply"):
        desc = job.get("description") or "No description available."
        st.markdown(desc[:2000] + ("…" if len(desc) > 2000 else ""))
        a, b, c = st.columns([1, 1, 1])
        a.link_button("Apply", job.get("url") or "#", use_container_width=True)
        if b.button("Unsave" if is_saved else "Save", key=f"s{key}",
                    use_container_width=True, type="secondary"):
            state["saved"].discard(key) if is_saved else state["saved"].add(key)
            st.rerun()
        if c.button("Not relevant", key=f"d{key}",
                    use_container_width=True, type="secondary"):
            state["dismissed"].add(key)
            st.rerun()
