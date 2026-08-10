"""
Presentation helpers for the Attuned UI — design tokens, inline SVG icons,
score rings and the distribution meter.

Inline SVG only: the spec forbids emoji anywhere in the interface.
"""

import textwrap
from typing import Dict, List

# ── Design tokens ─────────────────────────────────────────────────────────────
INK = "#0D1B2A"
SLATE = "#64748B"
ULTRAMARINE = "#2B59FF"
TEAL = "#06B6A0"
CORAL = "#FF6A45"
CANVAS = "#F4F6FB"
SURFACE = "#FFFFFF"
LINE = "#E3E9F2"
DANGER = "#E23D5C"

TINT_BLUE = "#EDF1FF"
TINT_TEAL = "#E4F8F4"
TINT_CORAL = "#FFF1EC"
TINT_NEUTRAL = "#F1F4F9"


def band(score: int) -> str:
    """Match band: teal at 70+, ultramarine 50-69, slate below."""
    if score >= 70:
        return "excellent"
    if score >= 50:
        return "good"
    return "low"


BAND_COLOR = {"excellent": TEAL, "good": ULTRAMARINE, "low": SLATE}


# ── Icons — 1.5px stroke, rounded caps ────────────────────────────────────────
def icon(name: str, size: int = 14, color: str = SLATE) -> str:
    paths = {
        "building": '<path d="M3 21h18M5 21V5a1 1 0 011-1h6a1 1 0 011 1v16M13 9h5a1 1 0 011 1v11"/>'
                    '<path d="M8 8h1M8 12h1M8 16h1M16 13h1M16 17h1"/>',
        "pin": '<path d="M12 21s7-5.6 7-11a7 7 0 10-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
        "wallet": '<path d="M3 7a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>'
                  '<path d="M16 12h3M3 9h16"/>',
        "calendar": '<path d="M4 6a2 2 0 012-2h12a2 2 0 012 2v13a1 1 0 01-1 1H5a1 1 0 01-1-1z"/>'
                    '<path d="M4 9h16M9 3v4M15 3v4"/>',
        "file": '<path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z"/><path d="M14 3v5h5"/>',
        "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
        "download": '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19h14"/>',
        "bookmark": '<path d="M6 4a1 1 0 011-1h10a1 1 0 011 1v16l-6-4-6 4z"/>',
        "close": '<path d="M6 6l12 12M18 6L6 18"/>',
        "sliders": '<path d="M4 8h10M18 8h2M4 16h4M12 16h8"/><circle cx="16" cy="8" r="2"/><circle cx="10" cy="16" r="2"/>',
        "external": '<path d="M14 4h6v6M20 4l-8 8"/><path d="M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/>',
        "globe": '<circle cx="12" cy="12" r="8"/><path d="M4 12h16M12 4a13 13 0 010 16A13 13 0 0112 4z"/>',
    }
    return (
        f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{paths.get(name, "")}</svg>'
    )


def wordmark() -> str:
    """
    Three-bar equalizer glyph + ATTUNED. Bar heights are set live from the
    match distribution by render_header, so the mark and the measurement are
    the same object seen twice.
    """
    return ""


def equalizer(excellent: int, good: int, low: int, title: str) -> str:
    total = max(excellent + good + low, 1)
    heights = [
        max(5, round(18 * excellent / total)),
        max(5, round(18 * good / total)),
        max(5, round(18 * low / total)),
    ]
    colors = [TEAL, ULTRAMARINE, SLATE]
    bars = "".join(
        f'<rect x="{i * 6}" y="{18 - h}" width="4" height="{h}" rx="2" fill="{c}"/>'
        for i, (h, c) in enumerate(zip(heights, colors))
    )
    return (f'<svg width="16" height="18" viewBox="0 0 16 18" role="img">'
            f'<title>{title}</title>{bars}</svg>')


def score_ring(score: int, size: int = 52) -> str:
    """Circular score ring with the value in mono at its centre."""
    colour = BAND_COLOR[band(score)]
    radius = 20
    circumference = 2 * 3.14159 * radius
    offset = circumference * (1 - max(0, min(score, 100)) / 100)
    return textwrap.dedent(f"""
        <svg class="ring" width="{size}" height="{size}" viewBox="0 0 48 48" role="img">
          <title>Match score {score} of 100</title>
          <circle cx="24" cy="24" r="{radius}" fill="none" stroke="{LINE}" stroke-width="3.5"/>
          <circle cx="24" cy="24" r="{radius}" fill="none" stroke="{colour}" stroke-width="3.5"
                  stroke-linecap="round" stroke-dasharray="{circumference:.1f}"
                  stroke-dashoffset="{offset:.1f}" transform="rotate(-90 24 24)"/>
          <text x="24" y="28" text-anchor="middle" class="ring-num" fill="{colour}">{score}</text>
        </svg>
    """).strip()


def distribution_meter(excellent: int, good: int, low: int) -> str:
    """3px bar forming the bottom edge of the results header."""
    total = max(excellent + good + low, 1)
    segments = [
        (excellent / total * 100, TEAL, f"{excellent} excellent"),
        (good / total * 100, ULTRAMARINE, f"{good} good"),
        (low / total * 100, SLATE, f"{low} low"),
    ]
    parts = "".join(
        f'<span class="meter-seg" style="width:{pct:.2f}%;background:{colour}" '
        f'title="{label}"></span>'
        for pct, colour, label in segments if pct > 0
    )
    return f'<div class="meter" role="img" aria-label="Match distribution">{parts}</div>'


def chip(label: str, kind: str = "neutral") -> str:
    """Tinted fill, 1px accent border, accent label — never a solid fill."""
    styles = {
        "teal": (TINT_TEAL, TEAL, "#04756A"),
        "blue": (TINT_BLUE, ULTRAMARINE, "#1E40D8"),
        "coral": (TINT_CORAL, CORAL, "#C2410C"),
        "neutral": (TINT_NEUTRAL, LINE, SLATE),
    }
    fill, border, text = styles.get(kind, styles["neutral"])
    return (f'<span class="chip" style="background:{fill};border-color:{border};color:{text}">'
            f'{label}</span>')


def stat_card(value, label: str, accent: str = SLATE) -> str:
    return textwrap.dedent(f"""
        <div class="stat">
          <div class="stat-num" style="color:{accent}">{value}</div>
          <div class="stat-lbl">{label}</div>
        </div>
    """).strip()


def esc(value) -> str:
    return (str(value or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def summarise(values: List[str], limit: int = 2, empty: str = "Any") -> str:
    """Muted one-line summary for a collapsed rail group."""
    if not values:
        return empty
    if len(values) <= limit:
        return ", ".join(values)
    return f"{len(values)} selected"


def styles() -> str:
    return textwrap.dedent(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap');

    /* ── Shell ── */
    .stApp {{ background: {CANVAS}; }}
    .stApp::before {{
        content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
        background:
          radial-gradient(60vw 60vw at 12% 8%, rgba(6,182,160,.08), transparent 60%),
          radial-gradient(55vw 55vw at 88% 92%, rgba(43,89,255,.08), transparent 60%);
    }}
    .block-container {{
        padding: 0 24px 40px 24px !important; max-width: none !important; position: relative; z-index: 1;
    }}
    header[data-testid="stHeader"] {{ background: transparent; height: 0; }}

    html, body, [class*="css"], .stApp {{ font-family: 'Inter', system-ui, sans-serif; }}

    /* ── Header bar ── */
    .appbar {{
        display: flex; align-items: center; gap: 14px;
        background: {INK}; margin: 0 -24px 18px -24px; padding: 0 24px;
        height: 64px; color: #fff;
    }}
    .brand {{ display: flex; align-items: center; gap: 9px; }}
    .brand-name {{
        font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
        font-size: 19px; letter-spacing: -.03em; color: #fff;
    }}
    .brand-name .d {{ color: {TEAL}; }}
    .tagline {{ color: #94A3B8; font-size: 13px; }}
    .appbar-right {{
        margin-left: auto; font-family: 'JetBrains Mono', monospace;
        font-size: 11px; color: #64748B; letter-spacing: .06em; text-transform: uppercase;
    }}

    /* ── Rail (sidebar) ── */
    section[data-testid="stSidebar"] {{
        background: {SURFACE}; width: 372px !important;
        box-shadow: 1px 0 0 rgba(13,27,42,.06), 4px 0 16px -6px rgba(13,27,42,.10);
        border-right: none;
    }}
    section[data-testid="stSidebar"] > div {{ padding-top: 12px; }}
    section[data-testid="stSidebar"] .block-container {{ padding: 16px 20px !important; }}
    section[data-testid="stSidebar"]::-webkit-scrollbar {{ width: 6px; }}
    section[data-testid="stSidebar"]::-webkit-scrollbar-thumb {{
        background: #D7DEEA; border-radius: 3px;
    }}

    .rail-label {{
        font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 500;
        text-transform: uppercase; letter-spacing: .08em; color: {SLATE};
        margin: 2px 0 6px 0; display: flex; justify-content: space-between; align-items: baseline;
    }}
    .rail-label .val {{ color: {INK}; }}
    .rail-foot {{
        background: {TINT_NEUTRAL}; border-radius: 10px; padding: 9px 12px; margin-top: 6px;
        font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .06em;
        color: {SLATE}; text-transform: uppercase;
        display: flex; align-items: center; gap: 7px;
    }}
    .dot {{ width: 6px; height: 6px; border-radius: 50%; background: {CORAL}; display: inline-block; }}

    /* ── Results header ── */
    .rhead {{
        display: flex; align-items: center; gap: 10px;
        padding: 11px 0 8px 0; border-bottom: none;
    }}
    .rhead-count {{
        font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
        font-size: 20px; color: {INK}; letter-spacing: -.025em;
    }}
    .rhead-sub {{
        font-family: 'JetBrains Mono', monospace; font-size: 11px; color: {SLATE};
        letter-spacing: .06em; text-transform: uppercase;
    }}
    .meter {{ display: flex; height: 3px; border-radius: 2px; overflow: hidden; background: {LINE};
              margin-bottom: 16px; transition: all .18s cubic-bezier(.2,.8,.2,1); }}
    .meter:hover {{ height: 10px; }}
    .meter-seg {{ transition: width .32s cubic-bezier(.2,.8,.2,1); }}

    /* ── Stat strip ── */
    .stat {{
        background: {SURFACE}; border-radius: 16px; padding: 14px 10px; text-align: center;
        box-shadow: 0 1px 2px rgba(13,27,42,.06), 0 10px 30px -12px rgba(13,27,42,.10);
    }}
    .stat-num {{
        font-family: 'JetBrains Mono', monospace; font-size: 23px; font-weight: 500;
        line-height: 1; font-variant-numeric: tabular-nums;
    }}
    .stat-lbl {{
        font-family: 'JetBrains Mono', monospace; font-size: 9.5px; color: {SLATE};
        text-transform: uppercase; letter-spacing: .08em; margin-top: 6px;
    }}

    /* ── Job card ── */
    .job {{
        background: {SURFACE}; border-radius: 16px; padding: 16px 18px; margin-bottom: 10px;
        border-left: 3px solid {LINE};
        box-shadow: 0 1px 2px rgba(13,27,42,.06), 0 10px 30px -12px rgba(13,27,42,.18);
        transition: transform .18s cubic-bezier(.2,.8,.2,1), box-shadow .18s cubic-bezier(.2,.8,.2,1);
    }}
    .job:hover {{ transform: translateY(-2px); box-shadow: 0 4px 8px rgba(13,27,42,.08), 0 18px 40px -14px rgba(13,27,42,.24); }}
    .job.excellent {{ border-left-color: {TEAL}; background: linear-gradient(90deg, {TINT_TEAL}55, {SURFACE} 40%); }}
    .job.good      {{ border-left-color: {ULTRAMARINE}; background: linear-gradient(90deg, {TINT_BLUE}55, {SURFACE} 40%); }}
    .job.low       {{ border-left-color: {SLATE}; }}

    .job-row {{ display: flex; gap: 16px; align-items: flex-start; }}
    .job-title {{
        font-family: 'Bricolage Grotesque', sans-serif; font-weight: 600; font-size: 17px;
        letter-spacing: -.02em; margin: 0 0 3px 0; line-height: 1.25;
    }}
    .job-title a {{ color: {INK}; text-decoration: none; }}
    .job-title a:hover {{ color: {ULTRAMARINE}; }}
    .job-meta {{
        display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px;
        font-size: 13px; color: {SLATE}; margin-bottom: 9px;
    }}
    .job-meta span {{ display: inline-flex; align-items: center; gap: 5px; }}
    .job-meta .mono {{ font-family: 'JetBrains Mono', monospace; font-size: 11px;
                       letter-spacing: .05em; text-transform: uppercase; }}
    .ic {{ flex-shrink: 0; }}
    .ring {{ flex-shrink: 0; }}
    .ring-num {{ font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 500; }}

    .chip {{
        display: inline-block; padding: 3px 10px; border-radius: 999px; border: 1px solid;
        font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 500;
        letter-spacing: .06em; text-transform: uppercase; margin: 2px 4px 2px 0;
        white-space: nowrap;
    }}

    /* ── Empty state ── */
    .empty {{ text-align: center; padding: 64px 20px; }}
    .empty h3 {{
        font-family: 'Bricolage Grotesque', sans-serif; font-weight: 600; font-size: 18px;
        color: {INK}; margin: 16px 0 6px 0;
    }}
    .empty p {{ color: {SLATE}; font-size: 14px; margin: 0; }}

    /* ── Streamlit widget restyling ── */
    div.stButton > button {{
        background: linear-gradient(135deg, {ULTRAMARINE}, #4B7BFF); color: #fff; border: none;
        border-radius: 10px; font-weight: 600; font-size: 14px; padding: .5rem 1rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 2px 8px rgba(43,89,255,.28);
        transition: transform .18s cubic-bezier(.2,.8,.2,1);
    }}
    div.stButton > button:hover {{ color: #fff; transform: translateY(-1px); }}
    div.stButton > button:focus {{ outline: 2px solid {ULTRAMARINE}; outline-offset: 2px; }}
    div.stButton > button[kind="secondary"] {{
        background: {SURFACE}; color: {INK}; border: 1px solid {LINE}; box-shadow: none;
    }}
    .stDownloadButton > button {{
        background: {SURFACE}; color: {INK}; border: 1px solid {LINE};
        border-radius: 10px; font-size: 13px; font-weight: 500; box-shadow: none;
    }}

    [data-testid="stExpander"] details {{
        border: none !important; border-radius: 10px !important;
        background: transparent !important; box-shadow: none;
    }}
    [data-testid="stExpander"] summary {{ padding: .3rem .1rem !important; }}
    [data-testid="stExpander"] summary p {{
        font-family: 'JetBrains Mono', monospace !important; font-size: 10.5px !important;
        text-transform: uppercase; letter-spacing: .08em; color: {SLATE} !important; margin: 0 !important;
    }}
    [data-testid="stExpander"] summary:hover p {{ color: {INK} !important; }}

    [data-testid="stWidgetLabel"] p {{
        font-family: 'JetBrains Mono', monospace !important; font-size: 10px !important;
        text-transform: uppercase; letter-spacing: .07em; color: {SLATE} !important;
        margin-bottom: 3px !important;
    }}
    .stTextInput input, [data-baseweb="select"] > div {{
        border-radius: 10px !important; border-color: {LINE} !important;
        background: {SURFACE} !important; font-size: 13.5px !important;
    }}
    .stTextInput input:focus {{ border-color: {ULTRAMARINE} !important;
                                box-shadow: 0 0 0 3px rgba(43,89,255,.14) !important; }}
    [data-baseweb="tag"] {{ background: {TINT_BLUE} !important; color: #1E40D8 !important;
                            border: 1px solid {ULTRAMARINE} !important; border-radius: 999px !important; }}
    [data-testid="stFileUploaderDropzone"] {{
        background: {TINT_NEUTRAL}; border: 1.5px dashed #C3CEE0; border-radius: 10px;
        padding: .5rem .8rem !important; min-height: 0 !important;
    }}
    [data-testid="stFileUploaderDropzoneInstructions"] small {{ display: none; }}
    [data-testid="stFileUploaderDropzoneInstructions"] {{ padding: 0 !important; }}
    [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{ box-shadow: 0 1px 4px rgba(13,27,42,.3); }}
    [data-testid="stCaptionContainer"] p {{ font-size: 11.5px !important; color: {SLATE} !important; }}
    [data-testid="stElementContainer"] {{ margin-bottom: 0 !important; }}
    [data-testid="stVerticalBlock"] {{ gap: .5rem !important; }}
    [data-testid="stCheckbox"] label p {{ font-size: 12.5px !important; color: {INK} !important; }}
    hr {{ border-color: {LINE}; margin: .8rem 0; }}

    @media (prefers-reduced-motion: reduce) {{
        * {{ transition: none !important; animation: none !important; }}
        .job:hover {{ transform: none; }}
    }}
    </style>
    """).strip()
