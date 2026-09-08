"""
Premium PwC design system for Streamlit Snowflake Monitor.
Includes premium layout components and backward-compatible helpers.
"""

import datetime
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

# ─── Premium PwC Palette ──────────────────────────────────────────────────────

COLORS = {
    # ── Base backgrounds ──────────────────────────────
    "bg_primary":           "#07090d",
    "bg_secondary":         "#0d1117",
    "bg_tertiary":          "#121822",
    "bg_card":              "#131a24",
    "bg_card_2":            "#18202c",
    "bg_card_hover":        "#1a2230",
    "bg_elevated":          "#1b2431",
    "bg_input":             "#10161f",
    "bg_overlay":           "rgba(255,255,255,0.03)",

    # ── Borders ───────────────────────────────────────
    "border":               "#263041",
    "border_light":         "#364255",
    "border_glow":          "rgba(208,74,2,0.18)",
    "border_accent":        "rgba(208,74,2,0.22)",

    # ── Text ──────────────────────────────────────────
    "text_primary":         "#f5f7fb",
    "text_secondary":       "#c4ccd8",
    "text_muted":           "#8b97a9",
    "text_dim":             "#5f6b7c",

    # ── PwC Brand ─────────────────────────────────────
    "pwc_orange":           "#D04A02",
    "pwc_orange_2":         "#E46A21",
    "pwc_orange_dark":      "#9F3600",
    "pwc_orange_light":     "#F26535",
    "pwc_orange_glow":      "rgba(208,74,2,0.35)",
    "pwc_gold":             "#FFB600",
    "pwc_gold_glow":        "rgba(255,182,0,0.35)",
    "pwc_tan":              "#D9C6A5",
    "pwc_black":            "#000000",

    # ── Functional colors ─────────────────────────────
    "green":                "#22c55e",
    "red":                  "#ef4444",
    "yellow":               "#f59e0b",
    "blue":                 "#3b82f6",
    "cyan":                 "#06b6d4",
    "purple":               "#8b5cf6",
    "pink":                 "#ec4899",
    "orange":               "#f97316",
    "teal":                 "#14b8a6",
    "indigo":               "#6366f1",

    # ── Glow effects ──────────────────────────────────
    "green_glow":           "rgba(34,197,94,0.35)",
    "red_glow":             "rgba(239,68,68,0.35)",
    "yellow_glow":          "rgba(245,158,11,0.35)",
    "blue_glow":            "rgba(59,130,246,0.35)",
    "cyan_glow":            "rgba(6,182,212,0.35)",
    "purple_glow":          "rgba(139,92,246,0.35)",
    "pink_glow":            "rgba(236,72,153,0.35)",
    "orange_glow":          "rgba(249,115,22,0.35)",
    "teal_glow":            "rgba(20,184,166,0.35)",

    # ── Shadows ───────────────────────────────────────
    "shadow_orange":        "rgba(208,74,2,0.25)",
    "shadow_blue":          "rgba(59,130,246,0.22)",
    "shadow_green":         "rgba(34,197,94,0.22)",
    "shadow_red":           "rgba(239,68,68,0.22)",
    "shadow_purple":        "rgba(139,92,246,0.22)",
    "shadow_gold":          "rgba(255,182,0,0.22)",

    # ── Legacy aliases ────────────────────────────────
    "accent_green":         "#22c55e",
    "accent_red":           "#ef4444",
    "accent_blue":          "#3b82f6",
    "accent_purple":        "#8b5cf6",
    "accent_cyan":          "#06b6d4",
    "accent_yellow":        "#f59e0b",
    "accent_orange":        "#D04A02",
    "accent_pink":          "#ec4899",
}

CHART_COLORS = [
    "#D04A02", "#FFB600", "#3b82f6", "#22c55e",
    "#8b5cf6", "#06b6d4", "#ec4899", "#f59e0b",
    "#94a3b8", "#14b8a6", "#f97316", "#6366f1"
]

ENV_COLORS = {
    "Production":  "#ef4444",
    "Development": "#3b82f6",
    "Staging":     "#f59e0b",
    "QA":          "#8b5cf6",
    "UAT":         "#22c55e",
    "Sandbox":     "#06b6d4",
}

def get_env_color(name: str) -> str:
    if name in ENV_COLORS:
        return ENV_COLORS[name]
    return CHART_COLORS[hash(name) % len(CHART_COLORS)]

# ─── Plotly Theme ─────────────────────────────────────────────────────────────

PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color=COLORS["text_primary"],
            family="Inter, sans-serif",
            size=12
        ),
        colorway=CHART_COLORS,
        title=dict(
            font=dict(size=16, color=COLORS["text_primary"])
        ),
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            linecolor=COLORS["border"],
            zerolinecolor=COLORS["border"],
            tickfont=dict(color=COLORS["text_secondary"]),
            title_font=dict(color=COLORS["text_secondary"]),
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            linecolor=COLORS["border"],
            zerolinecolor=COLORS["border"],
            tickfont=dict(color=COLORS["text_secondary"]),
            title_font=dict(color=COLORS["text_secondary"]),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(color=COLORS["text_secondary"])
        ),
        hoverlabel=dict(
            bgcolor=COLORS["bg_elevated"],
            bordercolor=COLORS["border_light"],
            font_color=COLORS["text_primary"],
            font_size=12,
        ),
        margin=dict(l=10, r=10, t=48, b=10),
    )
)

pio.templates["pwc_premium"] = PLOTLY_TEMPLATE
pio.templates.default = "pwc_premium"

# ─── Premium CSS Injection ────────────────────────────────────────────────────

# âââ CSS injection helper (Streamlit Community + Streamlit-in-Snowflake safe) â
def _inject_style(css: str):
    """Inject a global <style> block reliably.

    st.html() is the modern, SiS-supported path (Streamlit >= 1.33). Older
    Streamlit runtimes that some SiS environments pin fall back to st.markdown.
    """
    block = f"<style>{css}</style>"
    try:
        st.html(block)
    except Exception:
        st.markdown(block, unsafe_allow_html=True)

def inject_css():
    _inject_style(f"""
    /* ---- Hard dark base: keeps the app dark in Streamlit-in-Snowflake even
       if a later rule is dropped. No external @import (blocked by SiS CSP). ---- */
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section[data-testid="stMain"],
    .main {{
        background-color: {COLORS["bg_primary"]} !important;
        color: {COLORS["text_primary"]} !important;
    }}
    header[data-testid="stHeader"] {{
        background: rgba(0,0,0,0) !important;
    }}

    :root {{
        --bg-primary: {COLORS["bg_primary"]};
        --bg-secondary: {COLORS["bg_secondary"]};
        --bg-card: {COLORS["bg_card"]};
        --bg-card-2: {COLORS["bg_card_2"]};
        --bg-elevated: {COLORS["bg_elevated"]};
        --border: {COLORS["border"]};
        --border-light: {COLORS["border_light"]};
        --text-primary: {COLORS["text_primary"]};
        --text-secondary: {COLORS["text_secondary"]};
        --text-muted: {COLORS["text_muted"]};
        --orange: {COLORS["pwc_orange"]};
        --orange-2: {COLORS["pwc_orange_2"]};
        --gold: {COLORS["pwc_gold"]};
        --green: {COLORS["green"]};
        --red: {COLORS["red"]};
        --yellow: {COLORS["yellow"]};
        --blue: {COLORS["blue"]};
        --purple: {COLORS["purple"]};
        --cyan: {COLORS["cyan"]};
    }}

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }}

    .stApp {{
        background:
            radial-gradient(circle at top left, rgba(208,74,2,0.09), transparent 28%),
            radial-gradient(circle at top right, rgba(59,130,246,0.06), transparent 24%),
            linear-gradient(180deg, {COLORS["bg_secondary"]} 0%, {COLORS["bg_primary"]} 100%) !important;
        color: {COLORS["text_primary"]} !important;
    }}

    .block-container {{
        max-width: 100% !important;
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }}

    section[data-testid="stSidebar"] {{
        background:
            linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01)),
            {COLORS["bg_secondary"]} !important;
        border-right: 1px solid {COLORS["border"]} !important;
        backdrop-filter: blur(14px);
    }}

    section[data-testid="stSidebar"] > div {{
        padding-top: 0 !important;
    }}

    /* ---- Multipage navigation links (fix dim/low-contrast page names) ---- */
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNav"] a span,
    [data-testid="stSidebarNav"] li a,
    [data-testid="stSidebarNav"] li a span,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarNavLink"] span {{
        color: {COLORS["text_secondary"]} !important;
        opacity: 1 !important;
    }}

    [data-testid="stSidebarNav"] a:hover,
    [data-testid="stSidebarNav"] a:hover span,
    [data-testid="stSidebarNavLink"]:hover span {{
        color: {COLORS["text_primary"]} !important;
    }}

    /* Active page */
    [data-testid="stSidebarNav"] a[aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-current="page"] span,
    [data-testid="stSidebarNavLink"][aria-current="page"] span {{
        color: {COLORS["text_primary"]} !important;
        font-weight: 700 !important;
    }}

    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background: linear-gradient(135deg, rgba(208,74,2,0.16), rgba(255,182,0,0.08)) !important;
        border-radius: 10px !important;
    }}

    /* "View N more" expander text in the nav */
    [data-testid="stSidebarNav"] [data-testid="stSidebarNavSeparator"],
    [data-testid="stSidebarNav"] summary,
    [data-testid="stSidebarNav"] summary span {{
        color: {COLORS["text_muted"]} !important;
    }}

    h1, h2, h3, h4, h5, h6 {{
        color: {COLORS["text_primary"]} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }}

    p, span, label, li {{
        color: {COLORS["text_secondary"]};
    }}

    .stButton > button {{
        background:
            linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)),
            {COLORS["bg_elevated"]};
        color: {COLORS["text_primary"]};
        border: 1px solid {COLORS["border_light"]};
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.84rem;
        padding: 0.55rem 1rem;
        transition: all 0.25s ease;
        box-shadow: 0 4px 16px rgba(0,0,0,0.16);
    }}

    .stButton > button:hover {{
        transform: translateY(-1px);
        border-color: {COLORS["pwc_orange"]};
        color: {COLORS["pwc_orange"]};
        box-shadow: 0 10px 24px {COLORS["shadow_orange"]};
    }}

    .stButton > button[kind="primary"] {{
        background:
            linear-gradient(135deg, {COLORS["pwc_orange"]} 0%, {COLORS["pwc_orange_2"]} 100%);
        color: white;
        border: 1px solid transparent;
        box-shadow: 0 10px 24px {COLORS["shadow_orange"]};
    }}

    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stNumberInput input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {{
        background: rgba(255,255,255,0.025) !important;
        color: {COLORS["text_primary"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 12px !important;
    }}

    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {{
        border-color: {COLORS["pwc_orange"]} !important;
        box-shadow: 0 0 0 3px rgba(208,74,2,0.12) !important;
    }}

    [data-testid="stMetric"] {{
        background:
            linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.00)),
            {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 16px;
        padding: 16px !important;
        box-shadow: 0 10px 24px rgba(0,0,0,0.14);
    }}

    [data-testid="stMetricValue"] {{
        color: {COLORS["text_primary"]} !important;
        font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Liberation Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 1.45rem !important;
    }}

    [data-testid="stMetricLabel"] {{
        color: {COLORS["text_muted"]} !important;
        font-size: 0.68rem !important;
        text-transform: uppercase;
        letter-spacing: 0.09em;
    }}

    .stDataFrame {{
        border: 1px solid {COLORS["border"]};
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 10px 24px rgba(0,0,0,0.14);
    }}

    [data-testid="stVerticalBlockBorderWrapper"] {{
        background:
            linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)),
            {COLORS["bg_card"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 24px rgba(0,0,0,0.14);
    }}

    div[data-testid="stExpander"] {{
        background:
            linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)),
            {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 16px;
        overflow: hidden;
    }}

    div[data-testid="stExpander"] summary {{
        color: {COLORS["text_primary"]} !important;
        font-weight: 600;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        background: rgba(255,255,255,0.02);
        border: 1px solid {COLORS["border"]};
        border-radius: 16px;
        padding: 6px;
        gap: 6px;
        backdrop-filter: blur(12px);
    }}

    .stTabs [data-baseweb="tab"] {{
        color: {COLORS["text_muted"]};
        border-radius: 12px;
        padding: 10px 18px;
        font-weight: 600;
        font-size: 0.84rem;
        transition: all 0.22s ease;
    }}

    .stTabs [aria-selected="true"] {{
        background:
            linear-gradient(135deg, rgba(208,74,2,0.16), rgba(255,182,0,0.08)) !important;
        color: {COLORS["text_primary"]} !important;
        border: 1px solid rgba(208,74,2,0.32) !important;
        box-shadow: 0 8px 20px rgba(208,74,2,0.14);
    }}

    .premium-hero {{
        position: relative;
        overflow: hidden;
        border-radius: 24px;
        border: 1px solid rgba(255,255,255,0.06);
        background:
            radial-gradient(circle at 15% 20%, rgba(208,74,2,0.18), transparent 25%),
            radial-gradient(circle at 85% 15%, rgba(255,182,0,0.10), transparent 20%),
            radial-gradient(circle at 80% 80%, rgba(59,130,246,0.08), transparent 22%),
            linear-gradient(135deg, #11161f 0%, #0f141d 40%, #0a0f16 100%);
        padding: 28px 30px;
        box-shadow:
            0 30px 60px rgba(0,0,0,0.30),
            inset 0 1px 0 rgba(255,255,255,0.04);
        margin-bottom: 1.5rem;
    }}

    .hero-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 0.62rem;
        font-weight: 800;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: {COLORS["pwc_gold"]};
        background: rgba(255,182,0,0.08);
        border: 1px solid rgba(255,182,0,0.18);
        backdrop-filter: blur(8px);
        margin-bottom: 10px;
    }}

    .hero-title {{
        font-size: 1.95rem;
        line-height: 1.1;
        font-weight: 800;
        color: {COLORS["text_primary"]};
        letter-spacing: -0.04em;
        margin-bottom: 6px;
    }}

    .hero-subtitle {{
        font-size: 0.92rem;
        color: {COLORS["text_secondary"]};
        max-width: 880px;
    }}

    .hero-meta {{
        position: absolute;
        top: 24px;
        right: 24px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: flex-end;
    }}

    .hero-chip {{
        padding: 7px 12px;
        border-radius: 12px;
        font-size: 0.68rem;
        font-weight: 700;
        color: {COLORS["text_secondary"]};
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        backdrop-filter: blur(10px);
    }}

    .section-wrap {{
        margin-top: 0.25rem;
        margin-bottom: 0.75rem;
    }}

    .section-head {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 14px;
    }}

    .section-accent {{
        width: 4px;
        height: 18px;
        border-radius: 4px;
        background: linear-gradient(180deg, {COLORS["pwc_orange"]}, {COLORS["pwc_gold"]});
        box-shadow: 0 0 18px rgba(208,74,2,0.22);
        flex-shrink: 0;
    }}

    .section-title {{
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: {COLORS["pwc_tan"]};
        white-space: nowrap;
    }}

    .section-line {{
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, rgba(255,255,255,0.08), transparent);
    }}

    .kpi-premium {{
        position: relative;
        overflow: hidden;
        border-radius: 18px;
        padding: 18px 18px 16px;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.00)),
            {COLORS["bg_card"]};
        border: 1px solid rgba(255,255,255,0.06);
        box-shadow: 0 14px 28px rgba(0,0,0,0.16);
        transition: all 0.24s ease;
        height: 100%;
    }}

    .kpi-premium::before {{
        content: '';
        position: absolute;
        inset: 0 0 auto 0;
        height: 3px;
        background: var(--kpi-color, {COLORS["pwc_orange"]});
    }}

    .kpi-icon {{
        font-size: 1.15rem;
        margin-bottom: 10px;
        opacity: 0.95;
    }}

    .kpi-value {{
        font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Liberation Mono', monospace;
        font-size: 1.62rem;
        font-weight: 700;
        color: var(--kpi-color, {COLORS["text_primary"]});
        line-height: 1;
    }}

    .kpi-label {{
        margin-top: 7px;
        font-size: 0.66rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: {COLORS["text_muted"]};
    }}

    .kpi-sub {{
        margin-top: 6px;
        font-size: 0.72rem;
        color: {COLORS["text_secondary"]};
    }}

    .glass-card {{
        background:
            linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00)),
            rgba(19,26,36,0.82);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 16px 30px rgba(0,0,0,0.18);
        backdrop-filter: blur(14px);
    }}

    .env-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 0.64rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }}

    .status-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 0.64rem;
        font-weight: 700;
        border: 1px solid rgba(255,255,255,0.08);
    }}

    .status-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }}

    .status-dot.pulse {{
        animation: pulseStatus 1.8s infinite ease-in-out;
    }}

    @keyframes pulseStatus {{
        0%,100% {{ transform: scale(1); opacity: 1; }}
        50% {{ transform: scale(1.2); opacity: 0.6; }}
    }}

    .pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 10px;
        font-size: 0.66rem;
        font-weight: 700;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.03);
    }}

    .mono {{
        font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Liberation Mono', monospace;
    }}

    .muted {{
        color: {COLORS["text_muted"]};
    }}

    .small {{
        font-size: 0.72rem;
    }}

    .micro {{
        font-size: 0.64rem;
    }}

    .premium-divider {{
        height: 1px;
        background: linear-gradient(90deg, rgba(255,255,255,0.10), transparent);
        margin: 0.5rem 0 1rem 0;
    }}

    """)

# backward compatibility
inject_grafana_css = inject_css

# ─── Premium Components ───────────────────────────────────────────────────────

def pwc_header(title: str,
               subtitle: str = "",
               badge: str = "Powered By PwC Data & AI"):
    now = datetime.datetime.now().strftime("%b %d, %Y  %H:%M")
    st.markdown(f"""
    <div class="premium-hero">
        <div class="hero-meta">
            <div class="hero-chip">🕒 {now}</div>
            <div class="hero-chip">❄️ Snowflake Command Center</div>
        </div>
        <div class="hero-badge">{badge}</div>
        <div class="hero-title">{title}</div>
        <div class="hero-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def section_header(title: str):
    st.markdown(f"""
    <div class="section-wrap">
        <div class="section-head">
            <div class="section-accent"></div>
            <div class="section-title">{title}</div>
            <div class="section-line"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def grafana_panel(title: str):
    section_header(title)

def kpi_card(icon: str,
             value: str,
             label: str,
             color: str,
             sub: str = None) -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-premium" style="--kpi-color:{color};">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        {sub_html}
    </div>
    """

def stat_card(value: str,
              label: str,
              color: str = None,
              sub_text: str = None) -> str:
    c = color or COLORS["text_primary"]
    sub_html = f'<div class="kpi-sub">{sub_text}</div>' if sub_text else ""
    return f"""
    <div class="kpi-premium" style="--kpi-color:{c};">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        {sub_html}
    </div>
    """

def env_badge_html(name: str, connected: bool = True) -> str:
    color = get_env_color(name)
    dot   = COLORS["green"] if connected else COLORS["red"]
    pulse = "pulse" if connected else ""
    return f"""
    <span class="env-badge"
          style="background:{color}15;
                 border:1px solid {color}33;
                 color:{color};">
        <span class="status-dot {pulse}"
              style="background:{dot};
                     box-shadow:0 0 10px {dot};"></span>
        {name}
    </span>
    """

def env_badge(name: str) -> str:
    color = get_env_color(name)
    return f"""
    <span class="env-badge"
          style="background:{color}15;
                 border:1px solid {color}33;
                 color:{color};">
        {name}
    </span>
    """

def status_dot(status: str) -> str:
    s = str(status).lower()
    if s in ("connected","started","running","active","success","healthy"):
        color = COLORS["green"]
        pulse = "pulse"
    elif s in ("disconnected","failed","error","suspended","stopped"):
        color = COLORS["red"]
        pulse = ""
    else:
        color = COLORS["yellow"]
        pulse = ""
    return (f'<span class="status-dot {pulse}" '
            f'style="background:{color}; '
            f'box-shadow:0 0 10px {color};"></span>')

def premium_info_box(text: str,
                     accent: str = None,
                     icon: str = "ℹ️") -> str:
    accent = accent or COLORS["blue"]
    return f"""
    <div class="glass-card"
         style="border-left:4px solid {accent};">
        <div style="display:flex; gap:10px; align-items:flex-start;">
            <div style="font-size:1rem;">{icon}</div>
            <div style="font-size:0.82rem;
                 color:{COLORS["text_secondary"]};
                 line-height:1.6;">
                {text}
            </div>
        </div>
    </div>
    """

def premium_subtle_label(text: str) -> str:
    return f'<span class="micro muted">{text}</span>'