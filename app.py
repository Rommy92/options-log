import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client
from datetime import date, datetime, timedelta
import uuid
import json

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Options Log",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f0f0d !important;
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebarContent"] { padding: 1.2rem 0.8rem; }

/* ── Main ── */
.main { background: #131311; }
.block-container { padding-top: 3rem; padding-bottom: 2rem; background: #131311; }

/* ── Hide Streamlit top header bar ── */
header[data-testid="stHeader"] {
    background: #131311 !important;
    border-bottom: none !important;
}
[data-testid="stToolbar"] { display: none !important; }

/* ── Remove default metric boxes ── */
div[data-testid="metric-container"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

/* ── Stats bar ── */
.stats-bar {
    display: flex;
    gap: 2px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}
.stat-box {
    flex: 1;
    min-width: 100px;
    background: #1a1a17;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 6px;
    padding: 10px 14px;
}
.stat-label {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4a4a42;
    margin-bottom: 4px;
}
.stat-value {
    font-size: 16px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    color: #f0c03c;
    line-height: 1.2;
}
.stat-value.green { color: #a8d472; }
.stat-value.red { color: #e87070; }
.stat-value.muted { color: #5a5a52; }
.stat-value.white { color: #e8e6df; }
.stat-sub {
    font-size: 10px;
    color: #4a4a42;
    margin-top: 2px;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Legacy trade cards ── */
.trade-card {
    background: #1a1a17;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    padding: 12px 14px;
    position: relative;
}
.trade-card.call  { border-top: 2px solid rgba(112,168,232,0.5); }
.trade-card.put   { border-top: 2px solid rgba(240,192,60,0.5); }
.trade-card.stock { border-top: 2px solid rgba(120,120,110,0.4); }

.card-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    margin-bottom: 8px;
    line-height: 1.3;
}
.card-title.call  { color: #70a8e8; }
.card-title.put   { color: #f0c03c; }
.card-title.stock { color: #888880; }

.card-rows { display: flex; flex-direction: column; gap: 0; }
.card-row {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 8px;
    align-items: baseline;
    padding: 3px 0;
    border-bottom: 1px solid rgba(255,255,255,0.03);
}
.card-row:last-child { border-bottom: none; }
.card-row-label {
    font-size: 12px;
    color: #4a4a42;
    white-space: nowrap;
}
.card-row-value {
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
    color: #c8c6bf;
    text-align: left;
}
.card-row-value.amber { color: #f0c03c; }
.card-row-value.green { color: #a8d472; }
.card-row-value.red   { color: #e87070; }
.card-row-value.blue  { color: #70a8e8; }
.card-row-value.muted { color: #4a4a42; }

/* ── New horizontal open-position strips ── */
.position-strip {
    background: #0c0f10;
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 14px 16px 10px 16px;
    margin-bottom: 10px;
    overflow: hidden;
}
.position-strip.call  { border-top: 1px solid rgba(112,168,232,0.25); }
.position-strip.put   { border-top: 1px solid rgba(240,192,60,0.25); }
.position-strip.stock { border-top: 1px solid rgba(160,160,160,0.18); }

.position-topbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
}
.position-badges {
    display: flex;
    gap: 6px;
    align-items: center;
}
.pos-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 20px;
    padding: 0 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.05em;
    border: 1px solid rgba(255,255,255,0.06);
    font-family: 'Inter', sans-serif;
}
.pos-badge.call {
    color: #70a8e8;
    background: rgba(112,168,232,0.08);
}
.pos-badge.put {
    color: #f0c03c;
    background: rgba(240,192,60,0.08);
}
.pos-badge.stock {
    color: #9a9a92;
    background: rgba(255,255,255,0.04);
}
.pos-badge.sell {
    color: #a8d472;
    background: rgba(168,212,114,0.08);
}
.pos-badge.buy {
    color: #e87070;
    background: rgba(232,112,112,0.08);
}
.position-date {
    font-size: 11px;
    color: #b8b4a8;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.04em;
}

.position-grid {
    display: grid;
    grid-template-columns: repeat(10, minmax(90px, 1fr));
    gap: 18px;
    align-items: start;
    margin-bottom: 10px;
}
.position-grid.stock {
    grid-template-columns: repeat(5, minmax(90px, 1fr));
}
.pos-col { min-width: 0; }
.pos-label {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #645f52;
    margin-bottom: 4px;
    line-height: 1.2;
}
.pos-value {
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
    color: #d5d1c6;
    line-height: 1.25;
    white-space: nowrap;
}
.pos-value.amber { color: #f0c03c; }
.pos-value.green { color: #a8d472; }
.pos-value.red   { color: #e87070; }
.pos-value.blue  { color: #70a8e8; }
.pos-value.muted { color: #5c584d; }
.pos-value.white { color: #e8e6df; }

.position-divider {
    border-top: 1px solid rgba(255,255,255,0.035);
    margin-top: 2px;
    margin-bottom: 8px;
}

/* ── Section title ── */
.section-title {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #3a3a32;
    margin-bottom: 10px;
    margin-top: 24px;
}

/* ── Buttons ── */
.stButton button {
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    border-radius: 5px !important;
    transition: all 0.15s !important;
}
.stButton button[kind="primary"] {
    background: rgba(240,192,60,0.12) !important;
    border: 1px solid rgba(240,192,60,0.35) !important;
    color: #f0c03c !important;
}
.stButton button[kind="primary"]:hover {
    background: rgba(240,192,60,0.2) !important;
}
.stButton button[kind="secondary"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: #7a7a72 !important;
}
.stButton button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #c8c6bf !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    color: #4a4a42 !important;
    padding: 8px 16px !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #f0c03c !important;
    border-bottom: 2px solid #f0c03c !important;
}

/* ── Ticker header ── */
.ticker-header {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 4px;
}
.ticker-header-sym {
    font-size: 22px;
    font-weight: 700;
    color: #e8e6df;
    letter-spacing: 0.04em;
}
.ticker-header-basis {
    font-size: 12px;
    color: #4a4a42;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Sidebar ── */
.sidebar-title {
    font-size: 14px;
    font-weight: 700;
    color: #f0c03c;
    letter-spacing: 0.06em;
    margin-bottom: 16px;
}
.sidebar-section {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #3a3a32;
    margin: 16px 0 8px 4px;
}

/* ── Inputs ── */
.stTextInput input, .stNumberInput input {
    background: #1a1a17 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: #c8c6bf !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    font-size: 12px !important;
    color: #7a7a72 !important;
    background: #1a1a17 !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 5px !important;
}

/* ── Dataframe ── */
.stDataFrame { font-size: 12px !important; }

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.05) !important; }

/* ── Alerts ── */
.stAlert { font-size: 12px !important; }

/* ── Hide branding ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Auth ───────────────────────────────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True

    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:60vh;gap:8px">
        <div style="font-size:28px;font-weight:700;color:#f0c03c;letter-spacing:0.06em">◈ OPTIONS LOG</div>
        <div style="font-size:12px;color:#3a3a32;margin-bottom:24px">covered calls · cash-secured puts</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pw = st.text_input("", type="password", placeholder="Password", label_visibility="collapsed")
        if st.button("Enter", use_container_width=True, type="primary"):
            if pw == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

# ── Supabase ───────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

sb = get_supabase()

# ── DB helpers ─────────────────────────────────────────────────────
def load_tickers():
    res = sb.table("tickers").select("*").order("symbol").execute()
    return [r["symbol"] for r in res.data]

def add_ticker(symbol):
    try:
        sb.table("tickers").insert({"symbol": symbol.upper()}).execute()
        return True
    except Exception:
        return False

def remove_ticker(symbol):
    sb.table("tickers").delete().eq("symbol", symbol).execute()
    sb.table("trades").delete().eq("symbol", symbol).execute()

def load_trades(symbol=None):
    q = sb.table("trades").select("*").order("date", desc=True)
    if symbol:
        q = q.eq("symbol", symbol)
    res = q.execute()
    return res.data

def save_trade(trade):
    sb.table("trades").insert(trade).execute()

def update_trade(trade_id, updates):
    sb.table("trades").update(updates).eq("id", trade_id).execute()

def delete_trade(trade_id):
    sb.table("trades").delete().eq("id", trade_id).execute()

# ── yfinance helpers ───────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_price(symbol):
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        return round(float(info.last_price), 2)
    except Exception:
        return None

@st.cache_data(ttl=300)
def get_options_chain(symbol, option_type="calls"):
    try:
        t = yf.Ticker(symbol)
        exps = t.options
        today = date.today()
        results = []

        for exp in exps:
            exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if dte < 25 or dte > 55:
                continue

            chain = t.option_chain(exp)
            df = chain.calls if option_type == "calls" else chain.puts
            df = df.copy()
            df["expiry"] = exp
            df["dte"] = dte
            results.append(df)

        if not results:
            return pd.DataFrame()

        return pd.concat(results, ignore_index=True)

    except Exception:
        return pd.DataFrame()

# ── Calc helpers ───────────────────────────────────────────────────
def parse_date_safe(val):
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except Exception:
        return None

def days_between(a, b):
    if not a or not b:
        return 0
    try:
        da = datetime.strptime(str(a), "%Y-%m-%d").date() if isinstance(a, str) else a
        db = datetime.strptime(str(b), "%Y-%m-%d").date() if isinstance(b, str) else b
        return (db - da).days
    except Exception:
        return 0

def calc_projection(trades, symbol):
    opts = [t for t in trades if t["symbol"] == symbol and t["type"] != "Stock"]
    closed_opts = [t for t in opts if t.get("closed") and t.get("closed_date")]
    open_opts = [t for t in opts if not t.get("closed") and t.get("expiry")]

    def avg(lst):
        return sum(lst) / len(lst) if lst else None

    closed_dtes = [days_between(t["date"], t["closed_date"]) for t in closed_opts if days_between(t["date"], t["closed_date"]) > 0]
    closed_prems = [float(t["total_premium"] or 0) for t in closed_opts]
    avg_c_dte = avg(closed_dtes)
    avg_c_prem = avg(closed_prems)
    closed_proj = (avg_c_prem * (365 / avg_c_dte)) if (avg_c_dte and avg_c_prem and len(closed_opts) >= 3) else None
    closed_cycles = (365 / avg_c_dte) if avg_c_dte else None

    open_dtes = [days_between(t["date"], t["expiry"]) for t in open_opts if days_between(t["date"], t["expiry"]) > 0]
    open_prems = [float(t["total_premium"] or 0) for t in open_opts]
    avg_o_dte = avg(open_dtes)
    avg_o_prem = avg(open_prems)
    open_proj = (avg_o_prem * (365 / avg_o_dte)) if avg_o_dte and avg_o_prem else None
    open_cycles = (365 / avg_o_dte) if avg_o_dte else None

    stock = next(
        (t for t in trades if t["symbol"] == symbol and t["type"] == "Stock" and t["side"] == "Buy" and not t.get("closed")),
        None
    )
    basis = float(stock["premium"]) * float(stock.get("shares", 100)) if stock else None

    return {
        "closed_proj": closed_proj,
        "closed_cycles": closed_cycles,
        "avg_c_dte": avg_c_dte,
        "open_proj": open_proj,
        "open_cycles": open_cycles,
        "avg_o_dte": avg_o_dte,
        "basis": basis,
    }

def fmt_proj(proj_val, cycles, dte, basis):
    if not proj_val:
        return "—", "—", "—"
    dollar = f"${proj_val:,.0f}"
    pct = f"{(proj_val / basis * 100):.1f}%" if basis else "—"
    sub = f"{int(cycles)} cycles/yr · {int(dte)}d avg" if cycles and dte else "—"
    return dollar, pct, sub

def open_trade_sort_key(t):
    if t["type"] != "Stock" and t.get("expiry"):
        dte = days_between(date.today(), t["expiry"])
        dte = dte if dte >= 0 else 999999
        return (0, dte, str(t.get("date", "")))
    return (1, 999999, str(t.get("date", "")))

# ── Stat cols helper ───────────────────────────────────────────────
_STAT_COLORS = {
    "amber": "#f0c03c",
    "green": "#a8d472",
    "red": "#e87070",
    "white": "#e8e6df",
    "muted": "#4a4a42",
}

def render_stat_cols(stats):
    cols = st.columns(len(stats))
    for col, (lbl, val, color_key, sub) in zip(cols, stats):
        hex_color = _STAT_COLORS.get(color_key, "#f0c03c")
        sub_html = f'<div style="font-size:10px;color:#3a3a32;margin-top:2px;font-family:monospace">{sub}</div>' if sub else ""
        col.markdown(f"""
<div style="background:#1a1a17;border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:10px 14px">
    <div style="font-size:9px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#3a3a32;margin-bottom:4px">{lbl}</div>
    <div style="font-size:16px;font-weight:600;font-family:'JetBrains Mono',monospace;color:{hex_color};line-height:1.2">{val}</div>
    {sub_html}
</div>""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────
for key, default in [
    ("active_ticker", None),
    ("active_tab", "dashboard"),
    ("show_add_trade", False),
    ("show_quick_add", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Load data ──────────────────────────────────────────────────────
tickers = load_tickers()
all_trades = load_trades()

def ticker_open_count(sym):
    return sum(1 for t in all_trades if t["symbol"] == sym and not t.get("closed"))

tickers_sorted = sorted(tickers, key=ticker_open_count, reverse=True)

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">◈ OPTIONS LOG</div>', unsafe_allow_html=True)

    is_dash = st.session_state.active_tab == "dashboard"
    if st.button("⊞ Dashboard", use_container_width=True, type="primary" if is_dash else "secondary"):
        st.session_state.active_tab = "dashboard"
        st.session_state.active_ticker = None
        st.rerun()

    st.markdown('<div class="sidebar-section">Tickers</div>', unsafe_allow_html=True)

    for sym in tickers_sorted:
        sym_trades = [t for t in all_trades if t["symbol"] == sym]
        open_opts = [t for t in sym_trades if not t.get("closed") and t["type"] != "Stock"]
        open_count = sum(1 for t in sym_trades if not t.get("closed"))
        open_prem = sum(float(t.get("total_premium") or 0) for t in open_opts)
        closed_pnl_sym = sum(float(t.get("closed_pnl") or 0) for t in sym_trades if t.get("closed"))
        is_active = st.session_state.active_ticker == sym

        prem_label = (
            f"${open_prem:,.0f}" if open_prem else
            f"+${closed_pnl_sym:,.0f}" if closed_pnl_sym > 0 else
            f"-${abs(closed_pnl_sym):,.0f}" if closed_pnl_sym < 0 else "—"
        )

        col_sym, col_del = st.columns([5, 1])
        with col_sym:
            if st.button(
                f"{sym}   {open_count} open · {prem_label}",
                key=f"ticker_{sym}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.active_ticker = sym
                st.session_state.active_tab = "log"
                st.session_state.show_add_trade = False
                st.session_state.show_quick_add = False
                st.rerun()

        with col_del:
            if st.button("✕", key=f"del_ticker_{sym}", use_container_width=True, help=f"Remove {sym} and all its trades"):
                st.session_state[f"confirm_del_ticker_{sym}"] = True
                st.rerun()

        if st.session_state.get(f"confirm_del_ticker_{sym}"):
            st.warning(f"Delete **{sym}** and all {len(sym_trades)} trades?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Yes, delete", key=f"confirm_yes_{sym}", type="primary", use_container_width=True):
                    remove_ticker(sym)
                    if st.session_state.active_ticker == sym:
                        st.session_state.active_ticker = None
                        st.session_state.active_tab = "dashboard"
                    st.session_state.pop(f"confirm_del_ticker_{sym}", None)
                    st.rerun()
            with cc2:
                if st.button("Cancel", key=f"confirm_no_{sym}", use_container_width=True):
                    st.session_state.pop(f"confirm_del_ticker_{sym}", None)
                    st.rerun()

    st.markdown("---")
    col_inp, col_btn = st.columns([3, 1])
    with col_inp:
        new_sym = st.text_input("", placeholder="SYM", label_visibility="collapsed", key="new_sym_input")
    with col_btn:
        if st.button("+", use_container_width=True, type="primary") and new_sym:
            add_ticker(new_sym.upper())
            st.rerun()

    st.markdown("---")
    export_data = {"tickers": tickers, "trades": all_trades}
    st.download_button(
        label="↓ Export JSON",
        data=json.dumps(export_data, indent=2, default=str),
        file_name=f"options_backup_{date.today()}.json",
        mime="application/json",
        use_container_width=True
    )

    uploaded = st.file_uploader("Import JSON", type="json", label_visibility="collapsed")
    if uploaded:
        try:
            raw = json.loads(uploaded.read())
            import_tickers = raw.get("tickers", [])
            import_trades = raw.get("trades", [])
            st.warning(f"Import {len(import_trades)} trades for {len(import_tickers)} tickers?")

            if st.button("Confirm import", use_container_width=True):
                for sym in import_tickers:
                    try:
                        sb.table("tickers").insert({"symbol": sym}).execute()
                    except Exception:
                        pass

                for t in import_trades:
                    mapped = {
                        "id": str(t.get("id", "")),
                        "symbol": t.get("symbol"),
                        "type": t.get("type"),
                        "side": t.get("side"),
                        "date": t.get("date"),
                        "expiry": t.get("expiry"),
                        "strike": t.get("strike"),
                        "contracts": t.get("contracts"),
                        "shares": t.get("shares"),
                        "premium": t.get("premium"),
                        "total_premium": t.get("total_premium") or t.get("totalPremium"),
                        "spot": t.get("spot"),
                        "annualized": t.get("annualized"),
                        "notes": t.get("notes", ""),
                        "closed": t.get("closed", False),
                        "closed_date": t.get("closed_date") or t.get("closedDate"),
                        "closed_price": t.get("closed_price") or t.get("closedPrice"),
                        "closed_pnl": t.get("closed_pnl") or t.get("closedPnl"),
                    }
                    mapped = {k: v for k, v in mapped.items() if v is not None}
                    try:
                        sb.table("trades").upsert(mapped).execute()
                    except Exception:
                        pass

                st.success("Import complete!")
                st.rerun()

        except Exception as e:
            st.error(f"Invalid backup file: {e}")

    st.markdown("---")
    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── Dashboard ──────────────────────────────────────────────────────
def render_dashboard():
    st.markdown(
        '<div class="ticker-header"><span class="ticker-header-sym">Dashboard</span><span class="ticker-header-basis">all tickers · all time</span></div>',
        unsafe_allow_html=True
    )

    trades = all_trades
    closed = [t for t in trades if t.get("closed")]
    open_opts = [t for t in trades if not t.get("closed") and t["type"] != "Stock"]

    total_pnl = sum(float(t.get("closed_pnl") or 0) for t in closed)
    total_premium = sum(float(t.get("total_premium") or 0) for t in trades if t["type"] != "Stock")
    open_premium = sum(float(t.get("total_premium") or 0) for t in open_opts)
    wins = sum(1 for t in closed if float(t.get("closed_pnl") or 0) > 0)
    win_rate = f"{wins / len(closed) * 100:.0f}%" if closed else "—"
    open_anns = [float(t["annualized"]) for t in open_opts if t.get("annualized")]
    avg_ann = f"{sum(open_anns) / len(open_anns):.1f}%" if open_anns else "—"
    pnl_color = "green" if total_pnl >= 0 else "red"
    pnl_str = f"+${total_pnl:,.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):,.2f}"

    render_stat_cols([
        ("Realized P&L", pnl_str, pnl_color, None),
        ("All-time Premium", f"${total_premium:,.2f}", "white", None),
        ("Open at Risk", f"${open_premium:,.2f}" if open_premium else "—", "amber", None),
        ("Win Rate", win_rate, "white", f"{wins}/{len(closed)} trades"),
        ("Avg Open Ann.", avg_ann, "amber", None),
    ])

    st.markdown('<div class="section-title">Monthly premium collected — last 12 months</div>', unsafe_allow_html=True)

    monthly = {}
    for t in trades:
        if t["type"] != "Stock" and t.get("date"):
            key = str(t["date"])[:7]
            monthly[key] = monthly.get(key, 0) + float(t.get("total_premium") or 0)

    months = []
    today = date.today()
    for i in range(11, -1, -1):
        d = date(today.year, today.month, 1) - timedelta(days=i * 30)
        key = d.strftime("%Y-%m")
        months.append({"month": d.strftime("%b '%y"), "premium": monthly.get(key, 0)})

    max_prem = max((m["premium"] for m in months), default=1) or 1
    for row_start in range(0, 12, 6):
        row_months = months[row_start:row_start + 6]
        cols = st.columns(6)
        for col, m in zip(cols, row_months):
            prem = m["premium"]
            bar_pct = int(prem / max_prem * 100) if max_prem else 0
            val_str = f"${prem:,.0f}" if prem else "—"
            val_color = "#f0c03c" if prem > 0 else "#2a2a27"
            bar_color = "#f0c03c" if prem > 0 else "#1e1e1b"
            col.markdown(f"""
<div style="background:#1a1a17;border:1px solid rgba(255,255,255,0.05);border-radius:6px;padding:10px 12px">
    <div style="font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#3a3a32;margin-bottom:6px">{m['month']}</div>
    <div style="font-size:15px;font-weight:600;font-family:'JetBrains Mono',monospace;color:{val_color};margin-bottom:8px">{val_str}</div>
    <div style="height:3px;background:#1e1e1b;border-radius:2px">
        <div style="height:3px;width:{bar_pct}%;background:{bar_color};border-radius:2px"></div>
    </div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Open positions</div>', unsafe_allow_html=True)
    if open_opts:
        rows = []
        prices = {}
        for t in open_opts:
            sym = t["symbol"]
            if sym not in prices:
                prices[sym] = get_price(sym)
            price = prices.get(sym)
            ann = float(t["annualized"]) if t.get("annualized") else None
            dte_left = days_between(str(date.today()), t.get("expiry", "")) if t.get("expiry") else None
            dist_str = "—"
            if price and t.get("strike"):
                strike = float(t["strike"])
                dist = (strike - price) if t["type"] == "Call" else (price - strike)
                dist_pct = dist / price * 100
                dist_str = "ITM ⚠" if dist <= 0 else f"+{dist_pct:.1f}% (${abs(dist):.2f})"

            rows.append({
                "Symbol": sym,
                "Type": t["type"],
                "Ann %": f"{ann:.1f}%" if ann else "—",
                "Strike": f"${float(t['strike']):.2f}" if t.get("strike") else "—",
                "Expiry": t.get("expiry", "—"),
                "DTE": f"{dte_left}d" if dte_left is not None else "—",
                "Premium": f"${float(t['total_premium']):.2f}" if t.get("total_premium") else "—",
                "Live $": f"${price:.2f}" if price else "—",
                "% to strike": dist_str,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div style="color:#3a3a32;font-size:12px;padding:12px 0">No open positions</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Per-ticker summary</div>', unsafe_allow_html=True)
    ticker_rows = []
    for sym in tickers:
        sym_trades = [t for t in trades if t["symbol"] == sym]
        sym_closed = [t for t in sym_trades if t.get("closed")]
        sym_open = [t for t in sym_trades if not t.get("closed") and t["type"] != "Stock"]
        pnl = sum(float(t.get("closed_pnl") or 0) for t in sym_closed)
        op = sum(float(t.get("total_premium") or 0) for t in sym_open)
        proj = calc_projection(trades, sym)
        cp = fmt_proj(proj["closed_proj"], proj["closed_cycles"], proj["avg_c_dte"], proj["basis"])
        opP = fmt_proj(proj["open_proj"], proj["open_cycles"], proj["avg_o_dte"], proj["basis"])

        ticker_rows.append({
            "Ticker": sym,
            "Trades": len(sym_trades),
            "Open": len(sym_open),
            "Open premium": f"${op:.2f}" if op else "—",
            "Realized P&L": f"{'+' if pnl >= 0 else ''}${pnl:.2f}",
            "Proj/yr (hist)": cp[0],
            "% basis": cp[1],
            "Proj/yr (open)": opP[0],
            "% basis (open)": opP[1],
        })

    if ticker_rows:
        st.dataframe(pd.DataFrame(ticker_rows), use_container_width=True, hide_index=True)

# ── Open position strip HTML ───────────────────────────────────────
def build_open_position_strip_html(t, live_price):
    typ = str(t["type"]).lower()
    side = str(t["side"]).lower()
    date_str = str(t.get("date", ""))

    def metric(label, value, color="white"):
        return f"""
        <div class="pos-col">
            <div class="pos-label">{label}</div>
            <div class="pos-value {color}">{value}</div>
        </div>
        """

    if t["type"] != "Stock":
        strike = float(t.get("strike") or 0)
        expiry = str(t.get("expiry") or "—")
        contracts = int(t.get("contracts") or 1)
        premium_ct = float(t.get("premium") or 0)
        total_premium = float(t.get("total_premium") or 0)
        open_date = parse_date_safe(t.get("date"))
        expiry_date = parse_date_safe(t.get("expiry"))
        dte = (expiry_date - date.today()).days if expiry_date else None
        held = (date.today() - open_date).days if open_date else None
        ann = float(t["annualized"]) if t.get("annualized") else None

        dist_val = "—"
        dist_color = "white"
        if live_price and strike > 0:
            dist = (strike - live_price) if t["type"] == "Call" else (live_price - strike)
            dist_pct = (dist / live_price * 100) if live_price else 0
            if dist <= 0:
                dist_val = "ITM ⚠"
                dist_color = "red"
            else:
                dist_val = f"+${abs(dist):.2f} ({dist_pct:+.1f}%)"
                dist_color = "green" if dist_pct >= 10 else "amber"

        be_val = "—"
        if t["type"] == "Call":
            spot = float(t.get("spot") or 0)
            if spot > 0 and contracts > 0:
                be = spot - premium_ct
                be_val = f"${be:.2f}"
        else:
            if strike > 0:
                be = strike - premium_ct
                be_val = f"${be:.2f}"

        badge_left = "Call" if t["type"] == "Call" else "Put"
        badge_side = "Sell" if t["side"] == "Sell" else "Buy"

        grid_html = """
        <div class="position-grid">
        """ + \
        metric("Strike", f"${strike:,.0f}", "white") + \
        metric("Expiry", expiry, "white") + \
        metric("Contracts", f"{contracts}", "white") + \
        metric("Premium / ct", f"${premium_ct:.2f}", "amber") + \
        metric("Total premium", f"${total_premium:,.2f}", "green" if total_premium > 0 else "white") + \
        metric("Days to exp", f"{dte}d" if dte is not None else "—", "white") + \
        metric("Days held", f"{held}d" if held is not None else "—", "white") + \
        metric("Proj. annualized", f"{ann:.1f}%" if ann is not None else "—", "blue" if ann is not None else "white") + \
        metric("Distance to strike", dist_val, dist_color) + \
        metric("Downside breakeven", be_val, "white") + \
        """
        </div>
        """

        return f"""
        <div class="position-strip {typ}">
            <div class="position-topbar">
                <div class="position-badges">
                    <span class="pos-badge {typ}">{badge_left}</span>
                    <span class="pos-badge {side}">{badge_side}</span>
                </div>
                <div class="position-date">{date_str}</div>
            </div>
            {grid_html}
            <div class="position-divider"></div>
        </div>
        """

    shares = int(t.get("shares") or 0)
    buy_price = float(t.get("premium") or 0)
    total_cost = float(t.get("total_premium") or (shares * buy_price))
    open_date = parse_date_safe(t.get("date"))
    held = (date.today() - open_date).days if open_date else None

    live_val = "—"
    if live_price is not None:
        live_val = f"${live_price:.2f}"

    unreal_val = "—"
    unreal_color = "white"
    if live_price is not None and shares > 0 and buy_price > 0:
        unreal = (live_price - buy_price) * shares
        unreal_pct = ((live_price - buy_price) / buy_price) * 100
        sign = "+" if unreal >= 0 else ""
        unreal_val = f"{sign}${unreal:,.0f} ({unreal_pct:+.1f}%)"
        unreal_color = "green" if unreal >= 0 else "red"

    grid_html = """
    <div class="position-grid stock">
    """ + \
    metric("Shares", f"{shares}", "white") + \
    metric("Buy price", f"${buy_price:.2f}", "white") + \
    metric("Total cost", f"${total_cost:,.2f}", "white") + \
    metric("Days held", f"{held}d" if held is not None else "—", "white") + \
    metric("Live / Unrealized", f"{live_val} · {unreal_val}", unreal_color if unreal_val != "—" else "white") + \
    """
    </div>
    """

    return f"""
    <div class="position-strip stock">
        <div class="position-topbar">
            <div class="position-badges">
                <span class="pos-badge stock">Stock</span>
                <span class="pos-badge buy">Buy</span>
            </div>
            <div class="position-date">{date_str}</div>
        </div>
        {grid_html}
        <div class="position-divider"></div>
    </div>
    """

# ── Ticker view ────────────────────────────────────────────────────
def render_ticker(sym):
    trades = [t for t in all_trades if t["symbol"] == sym]
    open_trades = sorted([t for t in trades if not t.get("closed")], key=open_trade_sort_key)
    closed_trades = [t for t in trades if t.get("closed")]
    open_opts = [t for t in open_trades if t["type"] != "Stock"]

    all_premium = sum(float(t.get("total_premium") or 0) for t in trades if t["type"] != "Stock")
    net_premium = sum(float(t.get("closed_pnl") or 0) for t in closed_trades if t["type"] != "Stock")
    closed_pnl = sum(float(t.get("closed_pnl") or 0) for t in closed_trades)
    open_premium = sum(float(t.get("total_premium") or 0) for t in open_opts)
    wins = sum(1 for t in closed_trades if float(t.get("closed_pnl") or 0) > 0)
    win_rate_str = f"{wins / len(closed_trades) * 100:.0f}% ({wins}/{len(closed_trades)})" if len(closed_trades) >= 3 else "— (3+ needed)"
    proj = calc_projection(trades, sym)
    cp = fmt_proj(proj["closed_proj"], proj["closed_cycles"], proj["avg_c_dte"], proj["basis"])
    closed_opts_count = len([t for t in closed_trades if t["type"] != "Stock"])
    basis_str = f"BASIS ${proj['basis']:,.2f}" if proj["basis"] else "BASIS NOT SET"

    st.markdown(
        f'<div class="ticker-header"><span class="ticker-header-sym">{sym}</span><span class="ticker-header-basis">{basis_str}</span></div>',
        unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns([1, 1, 1, 4])
    with col1:
        if st.button("+ New trade", type="primary", use_container_width=True):
            st.session_state.show_add_trade = True
            st.session_state.show_quick_add = False
    with col2:
        if st.button("Quick log (closed)", use_container_width=True):
            st.session_state.show_quick_add = True
            st.session_state.show_add_trade = False

    tab1, tab2 = st.tabs(["TRADE LOG", "SCREENER"])

    with tab1:
        pnl_color = "green" if closed_pnl >= 0 else "red"
        pnl_str = f"+${closed_pnl:.2f}" if closed_pnl >= 0 else f"-${abs(closed_pnl):.2f}"
        proj_label = "PROJ / YR" if closed_opts_count >= 3 else f"PROJ/YR ({3 - closed_opts_count} more)"
        proj_val = cp[0] if closed_opts_count >= 3 else "—"
        proj_sub = cp[1] if closed_opts_count >= 3 else "(3+ closes)"

        render_stat_cols([
            ("Realized P&L", pnl_str, pnl_color, None),
            ("Gross Premium", f"${all_premium:.2f}", "white", None),
            ("Net Retained", f"${net_premium:.2f}", "white", None),
            ("Open Premium", f"${open_premium:.2f}" if open_premium else "—", "amber", None),
            ("Win Rate", win_rate_str, "white", None),
            (proj_label, proj_val, "amber", proj_sub),
        ])

        st.markdown('<div class="section-title">Open positions</div>', unsafe_allow_html=True)
        if open_trades:
            live_price = get_price(sym)

            for t in open_trades:
                st.markdown(build_open_position_strip_html(t, live_price), unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns([1.2, 1, 1, 4.8])
                with c1:
                    if st.button("✓ Close", key=f"close_{t['id']}", use_container_width=True, type="primary"):
                        st.session_state[f"closing_{t['id']}"] = True
                        st.session_state[f"editing_{t['id']}"] = False
                with c2:
                    if st.button("Edit", key=f"edit_{t['id']}", use_container_width=True):
                        st.session_state[f"editing_{t['id']}"] = True
                        st.session_state[f"closing_{t['id']}"] = False
                with c3:
                    if st.button("Delete", key=f"del_{t['id']}", use_container_width=True):
                        delete_trade(t["id"])
                        st.rerun()

                if st.session_state.get(f"closing_{t['id']}"):
                    render_close_form(t)
                if st.session_state.get(f"editing_{t['id']}"):
                    render_edit_form(t)
        else:
            st.markdown('<div style="color:#3a3a32;font-size:12px;padding:12px 0">No open positions</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">Closed trades</div>', unsafe_allow_html=True)
        if closed_trades:
            for t in closed_trades:
                is_opt = t["type"] != "Stock"
                dit = days_between(t["date"], t.get("closed_date", "")) if t.get("closed_date") else "—"
                pnl = float(t.get("closed_pnl") or 0)
                ann = f"{float(t['annualized']):.0f}%" if t.get("annualized") else "—"
                qty_str = f"@${float(t['strike']):.0f}" if (is_opt and t.get("strike")) else (f"{t.get('shares', '')}sh" if t.get("shares") else "")
                pnl_sign = "+" if pnl >= 0 else ""

                with st.expander(f"{t['date']} · {t['type']} {t['side']} {qty_str} · P&L: {pnl_sign}${pnl:.2f}"):
                    c1, c2, c3, c4, c5 = st.columns(5)

                    def _m(col, lbl, val):
                        col.markdown(
                            f'<div style="font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#3a3a32;margin-bottom:4px">{lbl}</div>'
                            f'<div style="font-size:14px;font-family:JetBrains Mono,monospace;color:#c8c6bf">{val}</div>',
                            unsafe_allow_html=True
                        )

                    _m(c1, "TYPE", f"{t['type']} {t['side']}")
                    _m(c2, "PREMIUM", f"${float(t['total_premium']):.2f}")
                    _m(c3, "P&L", f"{pnl_sign}${pnl:.2f}")
                    _m(c4, "DIT", f"{dit}d" if dit != "—" else "—")
                    _m(c5, "ANN %", ann)

                    if t.get("notes"):
                        st.markdown(f'<div style="font-size:11px;color:#4a4a42;margin-top:6px">✎ {t["notes"]}</div>', unsafe_allow_html=True)

                    st.markdown("")
                    col1, col2, col3 = st.columns([1, 1, 4])
                    with col1:
                        if st.button("Edit", key=f"edit_closed_{t['id']}"):
                            st.session_state[f"editing_{t['id']}"] = True
                            st.rerun()
                    with col2:
                        if st.button("Delete", key=f"del_closed_{t['id']}"):
                            delete_trade(t["id"])
                            st.rerun()

                if st.session_state.get(f"editing_{t['id']}"):
                    render_edit_form(t)
        else:
            st.markdown('<div style="color:#3a3a32;font-size:12px;padding:12px 0">No closed trades yet</div>', unsafe_allow_html=True)

    with tab2:
        render_screener(sym, trades)

# ── Edit form ──────────────────────────────────────────────────────
def render_edit_form(t):
    is_opt = t["type"] != "Stock"

    with st.form(key=f"edit_form_{t['id']}"):
        st.markdown(f"**Edit — {t['symbol']} {t['side']} {t['type']}**")
        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input("Open date", value=datetime.strptime(str(t["date"]), "%Y-%m-%d").date())
        with col2:
            new_notes = st.text_input("Notes", value=t.get("notes") or "")

        if is_opt:
            col3, col4, col5 = st.columns(3)
            with col3:
                new_premium = st.number_input("Premium/ct ($)", value=float(t.get("premium") or 0), step=0.01)
            with col4:
                new_strike = st.number_input("Strike ($)", value=float(t.get("strike") or 0), step=0.5)
            with col5:
                new_contracts = st.number_input("Contracts", value=int(t.get("contracts") or 1), step=1)

            exp_val = date.today()
            if t.get("expiry"):
                try:
                    exp_val = datetime.strptime(str(t["expiry"]), "%Y-%m-%d").date()
                except Exception:
                    pass

            new_expiry = st.date_input("Expiry", value=exp_val)
            new_spot = st.number_input("Stock price at open ($)", value=float(t.get("spot") or 0), step=0.01)
        else:
            col3, col4 = st.columns(2)
            with col3:
                new_price = st.number_input("Price/share ($)", value=float(t.get("premium") or 0), step=0.01)
            with col4:
                new_shares = st.number_input("Shares", value=int(t.get("shares") or 100), step=1)

        new_pnl = None
        if t.get("closed"):
            new_pnl = st.number_input("Realized P&L ($)", value=float(t.get("closed_pnl") or 0), step=1.0)

        submitted = st.form_submit_button("Save changes", type="primary")
        cancelled = st.form_submit_button("Cancel")

        if submitted:
            updates = {"date": str(new_date), "notes": new_notes}

            if new_pnl is not None:
                updates["closed_pnl"] = float(new_pnl)

            if is_opt:
                total = new_premium * 100 * int(new_contracts)
                ann = None
                if new_spot > 0:
                    dte = (new_expiry - new_date).days
                    if dte > 0:
                        ann = (total / (new_spot * 100 * new_contracts)) * (365 / dte) * 100

                updates.update({
                    "premium": float(new_premium),
                    "strike": float(new_strike),
                    "contracts": int(new_contracts),
                    "expiry": str(new_expiry),
                    "spot": float(new_spot),
                    "total_premium": float(total),
                    "annualized": round(ann, 2) if ann else t.get("annualized"),
                })
            else:
                updates.update({
                    "premium": float(new_price),
                    "shares": int(new_shares),
                    "total_premium": float(new_price * new_shares),
                })

            update_trade(t["id"], updates)
            st.session_state.pop(f"editing_{t['id']}", None)
            st.rerun()

        if cancelled:
            st.session_state.pop(f"editing_{t['id']}", None)
            st.rerun()

# ── Close form ─────────────────────────────────────────────────────
def render_close_form(t):
    is_opt = t["type"] != "Stock"

    with st.form(key=f"close_form_{t['id']}"):
        st.markdown(f"**Close — {t['symbol']} {t['side']} {t['type']}**")
        col1, col2 = st.columns(2)
        with col1:
            close_date = st.date_input("Close date", value=date.today())
        with col2:
            label = "Buy-back premium/contract ($)" if is_opt else "Sell price/share ($)"
            close_price = st.number_input(label, min_value=0.0, step=0.01)

        if close_price > 0:
            if is_opt:
                close_total = close_price * 100 * int(t.get("contracts", 1))
                pnl = float(t["total_premium"]) - close_total if t["side"] == "Sell" else close_total - float(t["total_premium"])
            else:
                pnl = (close_price - float(t["premium"])) * int(t.get("shares", 100))
            color = "#a8d472" if pnl >= 0 else "#e87070"
            sign = "+" if pnl >= 0 else ""
            st.markdown(
                f'<div style="font-size:14px;font-weight:600;color:{color};margin:8px 0">Realized P&L: {sign}${pnl:.2f}</div>',
                unsafe_allow_html=True
            )

        col_sub, col_can = st.columns(2)
        with col_sub:
            submitted = st.form_submit_button("Confirm close", type="primary")
        with col_can:
            cancelled = st.form_submit_button("Cancel")

        if submitted and close_price > 0:
            if is_opt:
                close_total = close_price * 100 * int(t.get("contracts", 1))
                pnl = float(t["total_premium"]) - close_total if t["side"] == "Sell" else close_total - float(t["total_premium"])
            else:
                pnl = (close_price - float(t["premium"])) * int(t.get("shares", 100))

            ann = None
            if is_opt and t.get("total_premium") and t.get("spot"):
                dit = days_between(t["date"], str(close_date))
                if dit > 0:
                    ann = float(t["total_premium"]) / (float(t["spot"]) * 100 * int(t.get("contracts", 1))) * (365 / dit) * 100

            update_trade(t["id"], {
                "closed": True,
                "closed_date": str(close_date),
                "closed_price": close_price,
                "closed_pnl": round(pnl, 2),
                "annualized": round(ann, 2) if ann else t.get("annualized"),
            })
            st.session_state.pop(f"closing_{t['id']}", None)
            st.rerun()

        if cancelled:
            st.session_state.pop(f"closing_{t['id']}", None)
            st.rerun()

# ── Add trade form ─────────────────────────────────────────────────
def render_add_trade_form(sym):
    with st.form("add_trade_form"):
        st.markdown(f"**New trade — {sym}**")

        col1, col2 = st.columns(2)
        with col1:
            trade_type = st.selectbox("Type", ["Call", "Put", "Stock"])
        with col2:
            side = st.selectbox("Side", ["Sell", "Buy"])

        col3, col4 = st.columns(2)
        with col3:
            trade_date = st.date_input("Open date", value=date.today())
        with col4:
            expiry = st.date_input("Expiration", value=date.today() + timedelta(days=35)) if trade_type != "Stock" else None

        is_opt = trade_type != "Stock"

        if is_opt:
            col5, col6 = st.columns(2)
            with col5:
                contracts = st.number_input("Contracts", min_value=1, value=1, step=1)
            with col6:
                strike = st.number_input("Strike price ($)", min_value=0.0, step=0.5)

            col7, col8 = st.columns(2)
            with col7:
                premium = st.number_input("Premium / contract ($)", min_value=0.0, step=0.01)

            open_stock = next(
                (
                    t for t in all_trades
                    if t["symbol"] == sym
                    and t["type"] == "Stock"
                    and t["side"] == "Buy"
                    and not t.get("closed")
                ),
                None
            )
            default_spot = float(open_stock["premium"]) if open_stock else 0.0

            with col8:
                spot = st.number_input(
                    "Stock price at open ($)",
                    min_value=0.0,
                    value=default_spot,
                    step=0.01,
                    help="Auto-filled from open stock position" if open_stock else "Used for annualized return calc"
                )

            if premium > 0:
                total_prem = premium * 100 * contracts
                st.success(f"Total premium: ${total_prem:.2f} ({contracts} × 100 × ${premium:.2f})")

                if spot > 0 and expiry:
                    dte = (expiry - trade_date).days
                    if dte > 0:
                        ann = (total_prem / (spot * 100 * contracts)) * (365 / dte) * 100
                        st.info(f"Projected annualized: {ann:.1f}%  ·  {dte}d to expiry")

                        if side == "Sell" and strike > 0:
                            if trade_type == "Call":
                                stock_gain = (strike - spot) * 100 * contracts
                                total_profit = stock_gain + total_prem
                                raw_pct = total_profit / (spot * 100 * contracts) * 100
                                st.warning(f"If assigned at ${strike}: ${total_profit:.2f} ({raw_pct:.1f}%)")
                            elif trade_type == "Put":
                                be = strike - premium
                                st.warning(f"If assigned at ${strike}: effective cost ${be:.2f}/sh")
        else:
            col5, col6 = st.columns(2)
            with col5:
                shares = st.number_input("Shares", min_value=1, value=100, step=1)
            with col6:
                stock_price = st.number_input("Price per share ($)", min_value=0.0, step=0.01)

            if stock_price > 0:
                st.success(f"Cost basis: ${stock_price * shares:,.2f} ({shares} shares × ${stock_price:.2f})")

        notes = st.text_input("Notes (optional)", placeholder="e.g. high IV, wheel trade...")

        col_sub, col_can = st.columns(2)
        with col_sub:
            submitted = st.form_submit_button("Add trade", type="primary")
        with col_can:
            cancelled = st.form_submit_button("Cancel")

        if submitted:
            trade_id = str(uuid.uuid4())
            trade = {
                "id": trade_id,
                "symbol": sym,
                "type": trade_type,
                "side": side,
                "date": str(trade_date),
                "notes": notes,
                "closed": False,
            }

            if is_opt:
                total_prem = premium * 100 * contracts
                ann = None
                if spot > 0 and expiry:
                    dte = (expiry - trade_date).days
                    if dte > 0:
                        ann = (total_prem / (spot * 100 * contracts)) * (365 / dte) * 100

                trade.update({
                    "expiry": str(expiry),
                    "strike": float(strike),
                    "contracts": int(contracts),
                    "premium": float(premium),
                    "total_premium": float(total_prem),
                    "spot": float(spot),
                    "annualized": round(ann, 2) if ann else None,
                })
            else:
                trade.update({
                    "shares": int(shares),
                    "premium": float(stock_price),
                    "total_premium": float(stock_price * shares),
                })

            save_trade(trade)
            st.session_state.show_add_trade = False
            st.rerun()

        if cancelled:
            st.session_state.show_add_trade = False
            st.rerun()

# ── Quick log ──────────────────────────────────────────────────────
def render_quick_add(sym):
    with st.form("quick_add_form"):
        st.markdown(f"**Quick log (closed) — {sym}**")

        col1, col2, col3 = st.columns(3)
        with col1:
            trade_type = st.selectbox("Type", ["Call", "Put", "Stock"])
        with col2:
            side = st.selectbox("Side", ["Sell", "Buy"])
        with col3:
            trade_date = st.date_input("Trade date", value=date.today())

        col4, col5, col6 = st.columns(3)
        with col4:
            total_premium = st.number_input("Premium collected ($)", min_value=0.0, step=1.0)
        with col5:
            realized_pnl = st.number_input("Realized P&L ($)", step=1.0)
        with col6:
            notes = st.text_input("Notes", placeholder="optional")

        col_sub, col_can = st.columns(2)
        with col_sub:
            submitted = st.form_submit_button("Log trade", type="primary")
        with col_can:
            cancelled = st.form_submit_button("Cancel")

        if submitted and total_premium >= 0:
            trade = {
                "id": str(uuid.uuid4()),
                "symbol": sym,
                "type": trade_type,
                "side": side,
                "date": str(trade_date),
                "notes": notes,
                "total_premium": float(total_premium),
                "premium": float(total_premium),
                "closed": True,
                "closed_date": str(trade_date),
                "closed_pnl": float(realized_pnl),
            }
            save_trade(trade)
            st.session_state.show_quick_add = False
            st.rerun()

        if cancelled:
            st.session_state.show_quick_add = False
            st.rerun()

# ── Screener ───────────────────────────────────────────────────────
def render_screener(sym, trades):
    st.markdown(
        '<div style="font-size:11px;color:#4a4a42;margin-bottom:12px">Live options chain · 25–55 DTE · ranked by return/safety score</div>',
        unsafe_allow_html=True
    )

    open_stock = next(
        (
            t for t in trades
            if t["symbol"] == sym
            and t["type"] == "Stock"
            and t["side"] == "Buy"
            and not t.get("closed")
        ),
        None
    )
    entry_price = float(open_stock["premium"]) if open_stock else None
    spot = get_price(sym)

    if entry_price:
        st.info(f"Entry: ${entry_price:.2f} · Live: ${spot:.2f}" if spot else f"Entry: ${entry_price:.2f}")

    col1, col2, col3 = st.columns(3)
    with col1:
        opt_type = st.selectbox("Option type", ["Calls", "Puts"], key="sc_type")
    with col2:
        min_otm = st.number_input("Min OTM %", value=2.0, step=0.5, key="sc_min_otm")
    with col3:
        fetch = st.button("Fetch chain", type="primary", key="sc_fetch")

    if fetch:
        with st.spinner("Fetching..."):
            df = get_options_chain(sym, opt_type.lower()[:-1] + "s")

        if df.empty:
            st.error("No contracts found")
            return

        basis = (entry_price or spot or 1) * 100
        results = []

        for _, row in df.iterrows():
            strike = float(row.get("strike", 0))
            bid = float(row.get("bid", 0) or 0)
            ask = float(row.get("ask", 0) or 0)
            mid = (bid + ask) / 2
            dte = int(row.get("dte", 30))
            expiry = str(row.get("expiry", ""))
            iv = float(row.get("impliedVolatility", 0) or 0)

            if mid <= 0 or strike <= 0:
                continue

            otm = ((strike - spot) / spot * 100) if (spot and opt_type == "Calls") else ((spot - strike) / spot * 100 if spot else 0)

            if otm < min_otm:
                continue

            total_prem = mid * 100
            ann_return = (total_prem / basis) * (365 / dte) * 100 if dte > 0 else 0

            assigned_str = "—"
            if opt_type == "Calls" and entry_price:
                stock_gain = (strike - entry_price) * 100
                total_profit = stock_gain + total_prem
                raw_pct = total_profit / (entry_price * 100) * 100
                assigned_str = f"${total_profit:.0f} ({raw_pct:.1f}%)"
            elif opt_type == "Puts":
                assigned_str = f"BE ${strike - mid:.2f}"

            safety = min(otm / 15, 1)
            ret_score = min(ann_return / 60, 1)
            score = ret_score * 0.6 + safety * 0.4
            grade = "A" if score > 0.8 else ("B" if score > 0.6 else ("C" if score > 0.4 else "D"))

            results.append({
                "Grade": grade,
                "Strike": f"${strike:.2f}",
                "Expiry": expiry,
                "DTE": dte,
                "Bid": f"${bid:.2f}",
                "Ask": f"${ask:.2f}",
                "Mid": f"${mid:.2f}",
                "Total $": f"${total_prem:.0f}",
                "Ann %": f"{ann_return:.1f}%",
                "If assigned": assigned_str,
                "OTM %": f"+{otm:.1f}%",
                "IV": f"{iv * 100:.0f}%" if iv else "—",
                "_score": score,
            })

        if not results:
            st.warning("No contracts passed filters")
            return

        results.sort(key=lambda x: x["_score"], reverse=True)
        for r in results:
            del r["_score"]

        st.markdown(
            f'<div style="font-size:11px;color:#4a4a42;margin-bottom:8px">{len(results)} contracts · top {min(30, len(results))} shown</div>',
            unsafe_allow_html=True
        )
        st.dataframe(pd.DataFrame(results[:30]), use_container_width=True, hide_index=True)

# ── Main render ────────────────────────────────────────────────────
if st.session_state.active_tab == "dashboard":
    render_dashboard()
elif st.session_state.active_ticker:
    sym = st.session_state.active_ticker
    if st.session_state.show_add_trade:
        render_add_trade_form(sym)
    elif st.session_state.show_quick_add:
        render_quick_add(sym)
    else:
        render_ticker(sym)
