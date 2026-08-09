import textwrap
import streamlit as st

from job_sources import (
    fetch_remotive, fetch_arbeitnow, fetch_jobicy,
    fetch_adzuna, fetch_jobspy, has_visa_sponsorship,
    normalize_job_type, infer_workplace,
    ADZUNA_COUNTRY_MAP, COUNTRIES, JOB_TYPES, WORKPLACE_TYPES, JOBSPY_AVAILABLE,
)
from scorer import score_jobs, build_profile
from cv_parser import extract_cv_text, guess_name, suggest_keywords

st.set_page_config(
    page_title="Job Hunter", page_icon="🎯",
    layout="wide", initial_sidebar_state="collapsed",
)


def html(markup: str) -> None:
    """
    Render raw HTML. The dedent matters: markdown treats any block indented by
    four spaces as a code block, so HTML written inside an indented Python
    block silently renders as literal text instead of markup.
    """
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


# ── Styles ────────────────────────────────────────────────────────────────────
html("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }

.stApp { background: #fbfcff; }
.block-container { padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1360px; }

/* ── Header ── */
.hero {
    background: linear-gradient(115deg, #e0f2fe 0%, #eef2ff 45%, #fce7f3 100%);
    border: 1px solid #dbeafe; border-radius: 14px;
    padding: 14px 22px; margin-bottom: 12px;
    display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap;
}
.hero h1 {
    font-size: 1.5rem; font-weight: 800; margin: 0; letter-spacing: -.4px;
    background: linear-gradient(90deg, #0ea5e9, #6366f1 55%, #ec4899);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero-sub { color: #7c8aa0; font-size: 12.5px; }

.sec { font-size: 10.5px; font-weight: 700; color: #a8b3c4;
       text-transform: uppercase; letter-spacing: .9px; margin: 0 0 4px 2px; }

/* ── Panels ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #fff; border-radius: 14px !important;
    border: 1px solid #e8edf6 !important; box-shadow: 0 1px 3px rgba(15,23,42,.04);
}

/* ── Compact controls ── */
[data-testid="stExpander"] details {
    border: 1px solid #eef2f7 !important; border-radius: 10px !important; background: #fbfcff !important;
}
[data-testid="stExpander"] summary { padding: .35rem .7rem !important; }
[data-testid="stExpander"] summary p { font-size: 12.5px !important; margin: 0 !important; }

[data-testid="stFileUploaderDropzone"] { padding: .45rem .8rem !important; min-height: 0 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] { padding: 0 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] small { display: none; }
[data-testid="stFileUploaderDropzone"] button { padding: .2rem .7rem !important; }

[data-testid="stWidgetLabel"] p { font-size: 11.5px !important; color: #94a3b8 !important;
                                  margin-bottom: 1px !important; }
[data-testid="stCaptionContainer"] p { font-size: 11.5px !important; margin-bottom: .2rem !important; }
[data-testid="stElementContainer"] { margin-bottom: 0 !important; }
[data-testid="stVerticalBlock"] { gap: .5rem !important; }
[data-testid="stSlider"] { padding-bottom: 0 !important; }
[data-testid="stCheckbox"] label p { font-size: 12.5px !important; color: #64748b !important; }

.stTextInput input, [data-baseweb="select"] > div {
    border-radius: 10px !important; border-color: #e2e8f0 !important; background: #fff !important;
}
.stTextInput input:focus { border-color: #a5b4fc !important; }
div[data-testid="stFileUploaderDropzone"] {
    background: #f8faff; border: 1.5px dashed #c7d2fe; border-radius: 12px;
}
[data-baseweb="tag"] { background: #eef2ff !important; color: #4338ca !important;
                       border-radius: 7px !important; }

div.stButton > button {
    background: linear-gradient(135deg, #22d3ee, #6366f1); color: #fff; border: none;
    border-radius: 11px; font-weight: 650; font-size: 14.5px; padding: .62rem 1rem;
    box-shadow: 0 2px 8px rgba(99,102,241,.28); transition: transform .12s, box-shadow .2s;
}
div.stButton > button:hover { color: #fff; transform: translateY(-1px);
                              box-shadow: 0 4px 14px rgba(99,102,241,.36); }

.stat { background: #fff; border: 1px solid #e8edf6; border-radius: 14px;
        padding: 15px 8px; text-align: center; }
.stat-num { font-size: 27px; font-weight: 800; line-height: 1; }
.stat-lbl { font-size: 11px; color: #94a3b8; margin-top: 5px; font-weight: 600;
            letter-spacing: .3px; text-transform: uppercase; }

.job { background: #fff; border: 1px solid #e8edf6; border-left: 5px solid #cbd5e1;
       border-radius: 14px; padding: 18px 22px; margin-bottom: 12px;
       box-shadow: 0 1px 3px rgba(15,23,42,.04); transition: box-shadow .2s, transform .1s; }
.job:hover { box-shadow: 0 6px 20px rgba(15,23,42,.09); transform: translateY(-2px); }
.job.excellent { border-left-color: #10b981; }
.job.good      { border-left-color: #f59e0b; }
.job.fair      { border-left-color: #fb923c; }
.job.poor      { border-left-color: #fb7185; }
.job.unscored  { border-left-color: #cbd5e1; }

.job-title { font-size: 16.5px; font-weight: 700; margin: 0 0 5px 0; }
.job-title a { color: #4f46e5; text-decoration: none; }
.job-title a:hover { text-decoration: underline; }
.job-meta { font-size: 12.5px; color: #7c8aa0; margin: 0 0 9px 0; }

.badge { display: flex; flex-direction: column; align-items: center; justify-content: center;
         border-radius: 14px; width: 70px; height: 70px; color: #fff; font-weight: 800; }
.badge-num { font-size: 24px; line-height: 1; }
.badge-lbl { font-size: 9.5px; opacity: .95; margin-top: 3px; letter-spacing: .4px; }

.pill { display: inline-block; padding: 3px 11px; border-radius: 20px;
        font-size: 11.5px; font-weight: 600; margin: 2px 4px 2px 0; }
.pill-match { background: #ecfdf5; color: #047857; border: 1px solid #d1fae5; }
.pill-visa  { background: #eff6ff; color: #1d4ed8; border: 1px solid #dbeafe; }
.pill-type  { background: #fffbeb; color: #b45309; border: 1px solid #fef3c7; }
.pill-place { background: #faf5ff; color: #7e22ce; border: 1px solid #f3e8ff; }
.pill-src   { background: #f8fafc; color: #64748b; border: 1px solid #eef2f7; }
.pill-skill { background: #eef2ff; color: #4338ca; border: 1px solid #e0e7ff; }

.apply { display: inline-block; background: linear-gradient(135deg, #22d3ee, #6366f1);
         color: #fff !important; font-weight: 650; font-size: 13.5px;
         padding: 9px 22px; border-radius: 10px; text-decoration: none; }
.apply:hover { opacity: .88; }

.empty { text-align: center; padding: 56px 20px; }
.empty .ico { font-size: 46px; }
.empty h3 { color: #475569; font-size: 18px; margin: 10px 0 4px 0; }
.empty p { color: #94a3b8; font-size: 14px; margin: 0; }
hr { margin: 1.1rem 0; border-color: #eef2f7; }
</style>
""")


html("""
<div class="hero">
  <h1>Job Hunter</h1>
  <span class="hero-sub">CV-matched roles across Indeed, LinkedIn &amp; remote boards</span>
</div>
""")


# ── CV upload + detected profile ──────────────────────────────────────────────
cv_col, skills_col = st.columns([1, 1.3], gap="small")

with cv_col:
    with st.container(border=True):
        st.caption("📄 **Your CV** — upload to enable relevance scoring. "
                   "You can still search without one.")
        uploaded = st.file_uploader(
            "cv", label_visibility="collapsed",
            type=["pdf", "docx", "doc", "md", "markdown", "txt"],
        )

if uploaded is not None and st.session_state.get("cv_filename") != uploaded.name:
    text, err = extract_cv_text(uploaded.name, uploaded.getvalue())
    st.session_state.update(cv_text=text, cv_filename=uploaded.name, cv_error=err)
    if text:
        st.session_state["kw_default"] = ", ".join(suggest_keywords(text))

cv_text: str = st.session_state.get("cv_text", "")
cv_error: str = st.session_state.get("cv_error", "")

with skills_col:
    with st.container(border=True):
        if cv_text:
            profile = build_profile(cv_text)
            name = guess_name(cv_text)
            st.caption(f"✨ **Detected profile{f' — {name}' if name else ''}** · "
                       f"{len(profile)} skills found")
            top = sorted(profile.items(), key=lambda x: x[1], reverse=True)[:12]
            html("".join(f'<span class="pill pill-skill">{t.title()}</span>' for t, _ in top))
        else:
            st.caption("✨ **Detected profile** — your skills appear here once a CV is uploaded.")
            html('<span class="pill pill-src">Roles</span>'
                 '<span class="pill pill-src">AI / ML</span>'
                 '<span class="pill pill-src">Tech stack</span>'
                 '<span class="pill pill-src">Process</span>'
                 '<span class="pill pill-src">Domain</span>')
        if cv_error:
            st.warning(cv_error, icon="⚠️")


# ── Search panel ──────────────────────────────────────────────────────────────
with st.container(border=True):
    html('<div class="sec">Search</div>')
    kw_col, btn_col = st.columns([6, 1], gap="small")
    keywords_raw = kw_col.text_input(
        "Keywords", label_visibility="collapsed",
        value=st.session_state.get("kw_default", "Project Manager, Data Analyst"),
        placeholder="Job titles, comma-separated — e.g. AI Project Manager, ML Engineer",
    )
    search_btn = btn_col.button("🔍  Search", use_container_width=True)

    s1, s2, s3 = st.columns([1.3, 1.6, 1], gap="small")
    source_options = ["Remotive", "Arbeitnow", "Jobicy"]
    if JOBSPY_AVAILABLE:
        source_options = ["Indeed", "LinkedIn"] + source_options
    sources = s1.multiselect(
        "Job sites", options=source_options,
        default=[s for s in ("Indeed", "LinkedIn", "Remotive") if s in source_options],
        placeholder="Choose sites…",
    )
    countries = s2.multiselect(
        "Countries", options=list(COUNTRIES.keys()),
        default=["Pakistan", "United Kingdom", "United States"],
        placeholder="Choose countries…",
    )
    city = s3.text_input("City / region", placeholder="Optional")

    f1, f2, f3, f4, f5, f6 = st.columns([1.2, 1.1, 1.1, 1, 1, 1], gap="small")
    job_types = f1.multiselect("Job type", options=JOB_TYPES, placeholder="Any")
    workplaces = f2.multiselect("Workplace", options=WORKPLACE_TYPES, placeholder="Any")
    sort_by = f3.selectbox("Sort by", ["Relevance ↓", "Most recent ↓", "Company A→Z"])
    min_score = f4.slider("Min score", 0, 100, 0, step=5)
    max_per_source = f5.slider("Per site", 5, 50, 20, step=5)
    with f6:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        visa_only = st.checkbox("✈️ Visa only")

    with st.expander("⚙️  Adzuna — optional extra coverage"):
        # Pre-filled from Streamlit secrets when deployed, so users of a hosted
        # instance don't have to paste keys on every visit.
        try:
            _sec_id = st.secrets.get("ADZUNA_APP_ID", "")
            _sec_key = st.secrets.get("ADZUNA_APP_KEY", "")
        except Exception:
            _sec_id = _sec_key = ""

        a1, a2, a3 = st.columns([1, 1, 1.6], gap="small")
        adzuna_id = a1.text_input("App ID", value=_sec_id, placeholder="xxxxxxxx")
        adzuna_key = a2.text_input("App Key", value=_sec_key, placeholder="xxxxxxxx", type="password")
        adzuna_countries = a3.multiselect(
            "Adzuna countries", options=list(ADZUNA_COUNTRY_MAP.keys()),
            default=["Pakistan", "United Kingdom", "UAE"],
        )
        st.caption("Free key at [developer.adzuna.com](https://developer.adzuna.com) — takes two minutes.")

st.markdown("")


# ── Search ────────────────────────────────────────────────────────────────────
if search_btn:
    keyword_list = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    if not keyword_list:
        st.warning("Enter at least one keyword.")
        st.stop()
    if not sources and not (adzuna_id and adzuna_key and adzuna_countries):
        st.warning("Choose at least one job site.")
        st.stop()

    jobspy_sites = [s.lower() for s in sources if s in ("Indeed", "LinkedIn")]
    board_sources = [s for s in sources if s in ("Remotive", "Arbeitnow", "Jobicy")]
    remote_wanted = workplaces == ["Remote"]

    tasks = []
    for kw in keyword_list:
        for s in board_sources:
            tasks.append((kw, s, None))
        if jobspy_sites:
            for c in (countries or ["United States"]):
                tasks.append((kw, "JobSpy", c))
        if adzuna_id and adzuna_key:
            for c in adzuna_countries:
                tasks.append((kw, "Adzuna", c))

    all_jobs, errors = [], []
    bar = st.progress(0.0, text="Fetching jobs…")

    for i, (kw, src, country) in enumerate(tasks, start=1):
        label = f"{src} · {country}" if country else src
        bar.progress(i / len(tasks), text=f"Fetching “{kw}” from {label}…")

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
            if "_error" in r:
                errors.append(f"{label}: {r['_error']}")
            else:
                all_jobs.append(r)

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

    with st.spinner(f"Scoring {len(unique)} jobs against your CV…"):
        unique = score_jobs(unique, cv_text)

    st.session_state["jobs"] = unique
    st.session_state["errors"] = errors

    if not unique:
        st.error("No jobs returned. Try different keywords, countries or job sites.")
    else:
        st.success(f"Found {len(unique)} unique jobs.")

if st.session_state.get("errors"):
    errs = st.session_state["errors"]
    with st.expander(f"⚠️  {len(errs)} source error(s) — some sites blocked or returned nothing"):
        for e in errs:
            st.caption(e)


# ── Results ───────────────────────────────────────────────────────────────────
jobs = st.session_state.get("jobs", [])

if not jobs:
    html("""
    <div class="empty">
      <div class="ico">🔍</div>
      <h3>Nothing to show yet</h3>
      <p>Upload your CV, set your keywords above, then hit Search.</p>
    </div>
    """)
    st.stop()

filtered = jobs[:]
if visa_only:
    filtered = [j for j in filtered if j.get("visa_sponsored")]
if job_types:
    filtered = [j for j in filtered if j.get("type_norm") in job_types]
if workplaces:
    filtered = [j for j in filtered if j.get("workplace") in workplaces]
filtered = [j for j in filtered if j.get("score", 0) >= min_score]

if sort_by == "Relevance ↓":
    filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
elif sort_by == "Most recent ↓":
    filtered.sort(key=lambda x: x.get("posted_at", ""), reverse=True)
else:
    filtered.sort(key=lambda x: (x.get("company") or "").lower())

if not filtered:
    st.warning(
        f"All {len(jobs)} fetched jobs were removed by your filters. "
        "Try lowering the minimum score or clearing the job type / workplace filters."
    )
    st.stop()

scores = [j.get("score", 0) for j in filtered]
stats = [
    (len(filtered), "Total", "#4f46e5"),
    (sum(scores) // len(scores), "Avg score", "#0ea5e9"),
    (sum(1 for s in scores if s >= 70), "Excellent", "#10b981"),
    (sum(1 for s in scores if 45 <= s < 70), "Good", "#f59e0b"),
    (sum(1 for j in filtered if j.get("visa_sponsored")), "Visa", "#3b82f6"),
    (sum(1 for j in filtered if j.get("workplace") == "Remote"), "Remote", "#ec4899"),
]
for col, (num, lbl, colr) in zip(st.columns(6, gap="small"), stats):
    with col:
        html(f'<div class="stat"><div class="stat-num" style="color:{colr}">{num}</div>'
             f'<div class="stat-lbl">{lbl}</div></div>')

st.markdown("")

CLASS = {"Excellent": "excellent", "Good": "good", "Fair": "fair",
         "Poor": "poor", "Unscored": "unscored"}
COLOR = {"Excellent": "#10b981", "Good": "#f59e0b", "Fair": "#fb923c",
         "Poor": "#fb7185", "Unscored": "#94a3b8"}
ICONS = {"Remotive": "🌐", "Arbeitnow": "🌍", "Jobicy": "💼",
         "Indeed": "🔵", "Linkedin": "🔗", "Adzuna": "🟠"}


def esc(text) -> str:
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


for job in filtered:
    level = job.get("match_level", "Unscored")
    color = COLOR.get(level, "#94a3b8")
    title = esc(job.get("title") or "Untitled")
    url = esc(job.get("url") or "#")
    source = esc(job.get("source"))
    icon = next((v for k, v in ICONS.items() if k in str(job.get("source"))), "📋")

    meta = "  ·  ".join(p for p in [
        f"🏢 {esc(job.get('company') or 'Unknown')}",
        f"📍 {esc(job.get('location'))}" if job.get("location") else "",
        f"💰 {esc(job.get('salary'))}" if job.get("salary") else "",
        f"🗓 {esc(job.get('posted_at'))}" if job.get("posted_at") else "",
    ] if p)

    pills = "".join(f'<span class="pill pill-match">✓ {esc(m)}</span>'
                    for m in job.get("key_matches", [])[:4])
    if job.get("type_norm"):
        pills += f'<span class="pill pill-type">⏱ {esc(job["type_norm"])}</span>'
    if job.get("workplace"):
        pills += f'<span class="pill pill-place">🏠 {esc(job["workplace"])}</span>'
    if job.get("visa_sponsored"):
        pills += '<span class="pill pill-visa">✈️ Visa sponsorship</span>'
    pills += f'<span class="pill pill-src">{icon} {source}</span>'

    badge = ""
    if job.get("scored"):
        badge = (f'<div class="badge" style="background:linear-gradient(135deg,{color},{color}bb)">'
                 f'<span class="badge-num">{job.get("score", 0)}</span>'
                 f'<span class="badge-lbl">{level.upper()}</span></div>')

    html(f"""
    <div class="job {CLASS.get(level, 'unscored')}">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:18px;">
        <div style="flex:1; min-width:0;">
          <p class="job-title"><a href="{url}" target="_blank">{title}</a></p>
          <p class="job-meta">{meta}</p>
          <div>{pills}</div>
        </div>
        <div style="flex-shrink:0;">{badge}</div>
      </div>
    </div>
    """)

    with st.expander(f"📄  Description & apply — {str(job.get('title'))[:60]}"):
        desc = job.get("description") or "No description available."
        st.markdown(desc[:2000] + ("…" if len(desc) > 2000 else ""))
        html(f'<a class="apply" href="{url}" target="_blank">Apply now →</a>')

html(f"<p style='text-align:center;color:#b6c2d4;font-size:12px;margin-top:22px'>"
     f"Showing {len(filtered)} of {len(jobs)} jobs</p>")
