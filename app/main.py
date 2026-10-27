import sys
from pathlib import Path
import streamlit as st  # pyright: ignore[reportMissingImports]  # noqa: E402
from common import page_setup
from config import config as cfg
from core import db

# Ensure root path is accessible
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 1. Initialize Page Setup without default st.title (to allow custom hero design)
page_setup("CyberShield AI", show_title=False, show_disclaimer=False)

# 2. Extract telemetry statistics
totals = db.summary()
total_flows = totals.get("total", 0)
attack_flows = totals.get("attack", 0)
anomaly_rate = (attack_flows / total_flows * 100) if total_flows > 0 else 0.0

# 3. Inject CSS styling matching the reference design:
# Deep dark obsidian theme, generous header breathing room, and fluted glass refraction
st.markdown(
    """
    <style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Container constraints with ample top padding so header is never cut */
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 1280px !important;
    }

    /* Transparent Streamlit header */
    [data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Hide default yellow alert box on main page */
    div[data-testid="stAlert"] {
        display: none !important;
    }

    /* Top Navigation Bar */
    .syna-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0.25rem 1.75rem 0.25rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 2.5rem;
        overflow: visible !important;
    }

    .syna-brand {
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #ffffff;
        text-transform: uppercase;
        user-select: none;
        line-height: 1.4 !important;
        padding-top: 6px;
    }

    .syna-brand .brand-reg {
        font-size: 0.95rem;
        font-weight: 400;
        vertical-align: super;
        color: #94a3b8;
    }

    .syna-nav-pills {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
    }

    .syna-nav-pill {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #cbd5e1;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 8px 18px;
        border-radius: 6px;
        letter-spacing: 0.75px;
        text-transform: uppercase;
        text-decoration: none;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        display: inline-block;
    }

    .syna-nav-pill:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff;
        border-color: rgba(255, 255, 255, 0.3);
        transform: translateY(-1px);
    }

    .syna-nav-pill.active {
        background: rgba(16, 185, 129, 0.15);
        border-color: rgba(16, 185, 129, 0.4);
        color: #34d399;
    }

    /* Hero Section Canvas */
    .hero-container {
        display: grid;
        grid-template-columns: 1.15fr 0.85fr;
        gap: 3rem;
        align-items: center;
        min-height: 420px;
        position: relative;
        margin-bottom: 2.5rem;
    }

    @media (max-width: 960px) {
        .hero-container {
            grid-template-columns: 1fr;
        }
    }

    /* Left Hero Content */
    .hero-left {
        display: flex;
        flex-direction: column;
        justify-content: center;
        z-index: 2;
    }

    .hero-badge-tag {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        width: fit-content;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 9999px;
        padding: 5px 14px;
        font-size: 0.725rem;
        font-weight: 600;
        color: #34d399;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 1.5rem;
    }

    .hero-badge-dot {
        width: 7px;
        height: 7px;
        background-color: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 10px #10b981;
        animation: pulseDot 2s infinite ease-in-out;
    }

    @keyframes pulseDot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }

    .hero-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: clamp(2.8rem, 5vw, 4.4rem);
        font-weight: 800;
        color: #ffffff;
        line-height: 1.06;
        letter-spacing: -1.8px;
        margin: 0 0 1.25rem 0;
        text-transform: uppercase;
    }

    .hero-subtitle {
        color: #cbd5e1;
        font-size: 1.15rem;
        line-height: 1.7;
        max-width: 580px;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }

    /* Right Hero Visual: Striated Fluted Glass & Luminous Green Nebula */
    .hero-visual-frame {
        position: relative;
        height: 420px;
        width: 100%;
        border-radius: 20px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        background: radial-gradient(circle at 75% 50%, rgba(16, 185, 129, 0.08) 0%, rgba(6, 8, 12, 0.95) 80%);
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    /* The glowing green aura portal */
    .green-glow-portal {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        width: 340px;
        height: 340px;
        border-radius: 50%;
        background: radial-gradient(circle at 45% 45%,
            rgba(74, 222, 128, 0.95) 0%,
            rgba(34, 197, 94, 0.8) 32%,
            rgba(16, 185, 129, 0.45) 58%,
            rgba(5, 46, 22, 0.1) 78%,
            transparent 88%);
        filter: blur(28px);
        box-shadow: 0 0 110px 40px rgba(34, 197, 94, 0.48);
        animation: portalFloat 7s ease-in-out infinite alternate;
    }

    @keyframes portalFloat {
        0% { transform: translateY(-50%) scale(0.96) rotate(0deg); opacity: 0.9; }
        100% { transform: translateY(-48%) scale(1.06) rotate(10deg); opacity: 1; }
    }

    /* Fluted glass refraction vertical slats overlay */
    .fluted-glass-container {
        position: absolute;
        inset: 0;
        display: flex;
        pointer-events: none;
        z-index: 3;
    }

    .fluted-slat {
        flex: 1;
        height: 100%;
        border-left: 1px solid rgba(255, 255, 255, 0.07);
        backdrop-filter: blur(14px) contrast(1.18) saturate(1.4);
        background: linear-gradient(180deg,
            rgba(255, 255, 255, 0.04) 0%,
            rgba(0, 0, 0, 0.12) 40%,
            rgba(255, 255, 255, 0.03) 70%,
            rgba(0, 0, 0, 0.22) 100%);
    }

    .fluted-slat:nth-child(even) {
        backdrop-filter: blur(22px) contrast(1.32) saturate(1.6) brightness(0.92);
        background: linear-gradient(180deg,
            rgba(0, 0, 0, 0.2) 0%,
            rgba(255, 255, 255, 0.05) 50%,
            rgba(0, 0, 0, 0.32) 100%);
    }

    .fluted-slat:first-child {
        border-left: none;
    }

    /* Section Cards Grid */
    .cyber-card {
        background: rgba(15, 20, 28, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.5rem;
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }

    .cyber-card:hover {
        border-color: rgba(16, 185, 129, 0.35);
        background: rgba(18, 26, 38, 0.85);
        box-shadow: 0 10px 30px -10px rgba(16, 185, 129, 0.15);
        transform: translateY(-2px);
    }

    .cyber-metric-value {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.1;
        margin: 0.5rem 0 0.3rem 0;
    }

    .cyber-metric-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #64748b;
    }

    .cyber-metric-sub {
        font-size: 0.8rem;
        color: #94a3b8;
    }

    /* Module Navigation Cards */
    .module-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.5rem;
        transition: all 0.25s ease;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 190px;
    }

    .module-card:hover {
        border-color: rgba(16, 185, 129, 0.4);
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        transform: translateY(-3px);
    }

    .module-badge {
        display: inline-block;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34d399;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        letter-spacing: 0.5px;
        margin-bottom: 0.75rem;
        width: fit-content;
    }

    .module-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.35rem;
    }

    .module-desc {
        font-size: 0.825rem;
        color: #94a3b8;
        line-height: 1.5;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 4. Render Top Navigation Bar (matching layout with CyberShield AI and direct page links)
st.markdown(
    """
    <div class="syna-navbar">
        <div class="syna-brand">
            CyberShield AI<span class="brand-reg">&reg;</span>
        </div>
        <div class="syna-nav-pills">
            <a href="/Live_Monitor" target="_self" class="syna-nav-pill">LIVE MONITOR</a>
            <a href="/Analytics" target="_self" class="syna-nav-pill">ANALYTICS</a>
            <a href="/Alert_Detail" target="_self" class="syna-nav-pill">ALERT DETAIL</a>
            <a href="/History_Reports" target="_self" class="syna-nav-pill">HISTORY REPORTS</a>
            <a href="http://localhost:8000/docs" target="_blank" class="syna-nav-pill">REST API &nearr;</a>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 5. Render Hero Section (clean title, designated description, and right green refraction frame)
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-left">
            <div class="hero-badge-tag">
                <span class="hero-badge-dot"></span>
                <span>Intelligent Intrusion Detection System</span>
            </div>
            <h1 class="hero-title">
                CyberShield AI
            </h1>
            <p class="hero-subtitle">
                Cyber shield AI is a network intrusion detection system prototype. It replays network flows through trained models and gives each detection attach a risk level.
            </p>
        </div>
        <div class="hero-visual-frame">
            <div class="green-glow-portal"></div>
            <div class="fluted-glass-container">
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
                <div class="fluted-slat"></div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 6. Real-Time Telemetry Stats Strip
st.markdown("<div id='quick-launch'></div>", unsafe_allow_html=True)
st.markdown("<h3 style='font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin-bottom: 1rem;'>System Telemetry Benchmark</h3>", unsafe_allow_html=True)

m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.markdown(
        f"""
        <div class="cyber-card">
            <div class="cyber-metric-label">Processed Flows</div>
            <div class="cyber-metric-value">{total_flows:,}</div>
            <div class="cyber-metric-sub">Held-out data vectors</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m_col2:
    st.markdown(
        f"""
        <div class="cyber-card">
            <div class="cyber-metric-label">Flagged Anomalies</div>
            <div class="cyber-metric-value" style="color: {'#f87171' if attack_flows > 0 else '#34d399'};">{attack_flows:,}</div>
            <div class="cyber-metric-sub"><b>{anomaly_rate:.2f}%</b> threat ratio</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m_col3:
    st.markdown(
        f"""
        <div class="cyber-card">
            <div class="cyber-metric-label">Active Classifier</div>
            <div class="cyber-metric-value" style="font-size: 1.6rem; color: #60a5fa;">{cfg.MODEL_NAME}</div>
            <div class="cyber-metric-sub">Latency: ~1.2ms / inference</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with m_col4:
    st.markdown(
        """
        <div class="cyber-card">
            <div class="cyber-metric-label">Explainability</div>
            <div class="cyber-metric-value" style="font-size: 1.6rem; color: #34d399;">TreeSHAP</div>
            <div class="cyber-metric-sub">Attribution vectors: 70 features</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)

# 7. Interactive Module Direct Launchers
st.markdown("<div id='features'></div>", unsafe_allow_html=True)
st.markdown("<h3 style='font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin-bottom: 1rem;'>Operational Console & Modules</h3>", unsafe_allow_html=True)

nav1, nav2 = st.columns(2)

with nav1:
    st.markdown(
        """
        <div class="module-card">
            <div>
                <span class="module-badge">STREAM ENGINE</span>
                <div class="module-title">Live Monitoring </div>
                <div class="module-desc">Start real-time stream replay, adjust flow playback speed, and watch live risk scores computed in real time.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Live_Monitor.py", label="Open Live Monitor ->", use_container_width=True)

with nav2:
    st.markdown(
        """
        <div class="module-card">
            <div>
                <span class="module-badge">DISTRIBUTIONS</span>
                <div class="module-title">Traffic Analytics</div>
                <div class="module-desc">Visualize protocol distributions, attack class compositions, and replay timeline activity once flows are processed.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Analytics.py", label="Open Analytics ->", use_container_width=True)

nav3, nav4 = st.columns(2)

with nav3:
    st.markdown(
        """
        <div class="module-card">
            <div>
                <span class="module-badge">EXPLAINABLE AI</span>
                <div class="module-title">Threat Attribution (SHAP)</div>
                <div class="module-desc">Inspect exact flow signatures, feature impact weights, heuristic risk calculations, and local SHAP contributions.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/4_Alert_Detail.py", label="Inspect Threat Signatures ->", use_container_width=True)

with nav4:
    st.markdown(
        """
        <div class="module-card">
            <div>
                <span class="module-badge">AUDIT & COMPLIANCE</span>
                <div class="module-title">History & Executive Reports</div>
                <div class="module-desc">Filter incident history by class and risk severity, download CSV audits, and export sanitized HTML SOC incident reports.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/5_History_Reports.py", label="Open Reports & Logs ->", use_container_width=True)

st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)

# 8. Architecture & How It Works Accordion
st.markdown("<div id='how-it-works'></div>", unsafe_allow_html=True)
with st.expander("How It Works: The 4-Tier CyberShield Telemetry Pipeline", expanded=False):
    st.markdown(
        """
        1. **Telemetry Ingestion & Replay**:
           Held-out network flows from the CIC-IDS2017 benchmark are streamed through the replay engine without modifying raw packets.
        2. **Multi-Class ML Inference**:
           Models (Trained XGBoost / Random Forest) evaluate 70 flow features (packet size distributions, inter-arrival times, TCP flags) in ~1.2ms.
        3. **Explainable Attribution (SHAP)**:
           TreeSHAP extracts exact local feature importance vectors, showing analysts precisely why a flow was flagged.
        4. **Heuristic Risk & Prescriptive Containment**:
           Confidence scores, feature extremity, and port sensitivity are synthesized into an analyst risk score (0-100).
        """
    )

# 9. FAQs & About section
st.markdown("<div id='faqs'></div>", unsafe_allow_html=True)
with st.expander("Frequently Asked Questions (FAQs)", expanded=False):
    st.markdown(
        """
        **Q: Is CyberShield AI actively monitoring live enterprise network traffic?**
        *A: No. CyberShield AI is a high-fidelity academic replay and training prototype operating on held-out CIC-IDS2017 vectors. It operates strictly read-only and never blocks traffic.*

        **Q: How is the heuristic risk score calculated?**
        *A: The risk score is composed of model class severity (40%), model prediction confidence (30%), flow volume/packet intensity (20%), and targeted destination port sensitivity (10%).*

        **Q: How do I query the platform programmatically?**
        *A: Launch the REST API server via `run_api.bat` or `uvicorn core.api:app --reload` and visit `http://localhost:8000/docs` to test endpoints.*
        """
    )

# 10. Analyst Notice Callout (Safety & Academic Integrity)
st.markdown(
    """
    <div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.25); border-left: 4px solid #10b981; border-radius: 8px; padding: 1rem 1.25rem; margin-top: 1.5rem; font-size: 0.85rem; color: #cbd5e1; line-height: 1.6;">
        <b style="color: #34d399;">Analyst Notice & Academic Sandbox:</b> CyberShield AI is an educational telemetry intrusion detection prototype.
        The risk score is a heuristic calculated using calibrated weights configured in <code>config/config.py</code>.
        The recommended defensive steps are suggestions for SOC analyst training; the application operates in read-only replay simulation mode and never blocks live traffic.
    </div>
    """,
    unsafe_allow_html=True,
)
