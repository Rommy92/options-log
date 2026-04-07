import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from supabase import create_client
from datetime import date, datetime, timedelta
import uuid

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
[data-testid="stSidebar"] { background: #161714; }
[data-testid="stSidebarContent"] { padding-top: 1rem; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
div[data-testid="metric-container"] {
    background: #1e1f1c;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 12px 16px;
}
div[data-testid="metric-container"] label { font-size: 11px !important; color: #7a7a72 !important; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 20px !important; }
.trade-card {
    background: #161714;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 10px;
}
.tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    margin-right: 4px;
}
.tag-call { background: rgba(112,168,232,0.15); color: #70a8e8; }
.tag-put  { background: rgba(240,192,96,0.12);  color: #f0c060; }
.tag-stock{ background: rgba(255,255,255,0.06); color: #7a7a72; }
.tag-sell { background: rgba(168,212,114,0.12); color: #a8d472; }
.tag-buy  { background: rgba(232,112,112,0.12); color: #e87070; }
.green { color: #a8d472; }
.red   { color: #e87070; }
.amber { color: #f0c060; }
.blue  { color: #70a8e8; }
.muted { color: #7a7a72; }
.section-title {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #7a7a72;
    margin-bottom: 8px;
    margin-top: 20px;
}
stDataFrame { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Auth ───────────────────────────────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown("## ◈ Options Log")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        pw = st.text_input("Password", type="password", placeholder="Enter password")
        if st.button("Login", use_container_width=True):
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
    except:
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
    except:
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
    except Exception as e:
        return pd.DataFrame()

# ── Calc helpers ───────────────────────────────────────────────────
def days_between(a, b):
    if not a or not b:
        return 0
    try:
        da = datetime.strptime(str(a), "%Y-%m-%d").date() if isinstance(a, str) else a
        db = datetime.strptime(str(b), "%Y-%m-%d").date() if isinstance(b, str) else b
        return (db - da).days
    except:
        return 0

def calc_projection(trades, symbol):
    opts = [t for t in trades if t["symbol"] == symbol and t["type"] != "Stock"]
    closed_opts = [t for t in opts if t.get("closed") and t.get("closed_date")]
    open_opts   = [t for t in opts if not t.get("closed") and t.get("expiry")]

    def avg(lst): return sum(lst) / len(lst) if lst else None

    closed_dtes  = [days_between(t["date"], t["closed_date"]) for t in closed_opts if days_between(t["date"], t["closed_date"]) > 0]
    closed_prems = [float(t["total_premium"] or 0) for t in closed_opts]
    avg_c_dte    = avg(closed_dtes)
    avg_c_prem   = avg(closed_prems)
    closed_proj  = (avg_c_prem * (365 / avg_c_dte)) if avg_c_dte and avg_c_prem else None
    closed_cycles= (365 / avg_c_dte) if avg_c_dte else None

    open_dtes  = [days_between(t["date"], t["expiry"]) for t in open_opts if days_between(t["date"], t["expiry"]) > 0]
    open_prems = [float(t["total_premium"] or 0) for t in open_opts]
    avg_o_dte  = avg(open_dtes)
    avg_o_prem = avg(open_prems)
    open_proj  = (avg_o_prem * (365 / avg_o_dte)) if avg_o_dte and avg_o_prem else None
    open_cycles= (365 / avg_o_dte) if avg_o_dte else None

    stock = next((t for t in trades if t["symbol"] == symbol and t["type"] == "Stock" and t["side"] == "Buy" and not t.get("closed")), None)
    basis = float(stock["premium"]) * float(stock.get("shares", 100)) if stock else None

    return {
        "closed_proj": closed_proj, "closed_cycles": closed_cycles, "avg_c_dte": avg_c_dte,
        "open_proj": open_proj,     "open_cycles": open_cycles,     "avg_o_dte": avg_o_dte,
        "basis": basis
    }

def fmt_proj(proj_val, cycles, dte, basis):
    if not proj_val:
        return "—", "—", "—"
    dollar = f"${proj_val:,.0f}"
    pct    = f"{(proj_val/basis*100):.1f}%" if basis else "—"
    sub    = f"{int(cycles)} cycles/yr · {int(dte)}d avg" if cycles and dte else "—"
    return dollar, pct, sub

# ── Session state ──────────────────────────────────────────────────
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "dashboard"
if "show_add_trade" not in st.session_state:
    st.session_state.show_add_trade = False
if "show_quick_add" not in st.session_state:
    st.session_state.show_quick_add = False

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ◈ Options Log")
    st.markdown("---")

    if st.button("◈ Dashboard", use_container_width=True,
                 type="primary" if st.session_state.active_tab == "dashboard" else "secondary"):
        st.session_state.active_tab = "dashboard"
        st.session_state.active_ticker = None
        st.rerun()

    st.markdown("**Tickers**")
    tickers = load_tickers()
    all_trades = load_trades()

    # Sort tickers by number of open trades descending
    def ticker_open_count(sym):
        return sum(1 for t in all_trades
                   if t["symbol"] == sym and not t.get("closed"))

    tickers_sorted = sorted(tickers, key=ticker_open_count, reverse=True)

    for sym in tickers_sorted:
        sym_trades = [t for t in all_trades if t["symbol"] == sym]
        open_prem = sum(float(t.get("total_premium") or 0)
                        for t in sym_trades if not t.get("closed") and t["type"] != "Stock")
        open_count = sum(1 for t in sym_trades if not t.get("closed"))
        closed_pnl = sum(float(t.get("closed_pnl") or 0) for t in sym_trades if t.get("closed"))
        prem_str = f"${open_prem:.0f}" if open_prem else "—"
        pnl_str = f"+${closed_pnl:.0f}" if closed_pnl > 0 else (f"-${abs(closed_pnl):.0f}" if closed_pnl < 0 else "")
        col1, col2 = st.columns([2, 1])
        with col1:
            is_active = st.session_state.active_ticker == sym
            if st.button(sym, key=f"ticker_{sym}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.active_ticker = sym
                st.session_state.active_tab = "log"
                st.rerun()
        with col2:
            color = "green" if open_prem > 0 else ("red" if closed_pnl < 0 else "")
            label = prem_str if open_prem else (pnl_str or "—")
            st.markdown(f'<span class="{color}" style="font-size:11px;line-height:2.4">{label}</span>', unsafe_allow_html=True)

    st.markdown("---")
    new_sym = st.text_input("Add ticker", placeholder="AAPL", label_visibility="collapsed")
    if st.button("+ Add", use_container_width=True) and new_sym:
        add_ticker(new_sym.upper())
        st.rerun()

    st.markdown("---")

    # Export
    export_data = {"tickers": tickers, "trades": all_trades}
    import json
    st.download_button(
        label="↓ Export backup",
        data=json.dumps(export_data, indent=2, default=str),
        file_name=f"options_backup_{date.today()}.json",
        mime="application/json",
        use_container_width=True
    )

    # Import
    uploaded = st.file_uploader("↑ Import backup", type="json", label_visibility="collapsed")
    if uploaded:
        try:
            raw = json.loads(uploaded.read())
            import_tickers = raw.get("tickers", [])
            import_trades  = raw.get("trades", [])
            st.warning(f"Import {len(import_trades)} trades for {len(import_tickers)} tickers?")
            if st.button("Confirm import", use_container_width=True):
                for sym in import_tickers:
                    try:
                        sb.table("tickers").insert({"symbol": sym}).execute()
                    except: pass
                for t in import_trades:
                    # Map camelCase keys from HTML backup to snake_case
                    mapped = {
                        "id":            str(t.get("id", "")),
                        "symbol":        t.get("symbol"),
                        "type":          t.get("type"),
                        "side":          t.get("side"),
                        "date":          t.get("date"),
                        "expiry":        t.get("expiry"),
                        "strike":        t.get("strike"),
                        "contracts":     t.get("contracts"),
                        "shares":        t.get("shares"),
                        "premium":       t.get("premium"),
                        "total_premium": t.get("total_premium") or t.get("totalPremium"),
                        "spot":          t.get("spot"),
                        "annualized":    t.get("annualized"),
                        "notes":         t.get("notes", ""),
                        "closed":        t.get("closed", False),
                        "closed_date":   t.get("closed_date") or t.get("closedDate"),
                        "closed_price":  t.get("closed_price") or t.get("closedPrice"),
                        "closed_pnl":    t.get("closed_pnl") or t.get("closedPnl"),
                    }
                    mapped = {k: v for k, v in mapped.items() if v is not None}
                    try:
                        sb.table("trades").upsert(mapped).execute()
                    except: pass
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
    st.markdown("## Dashboard")
    st.markdown("*All tickers · all time*")

    trades = all_trades
    closed = [t for t in trades if t.get("closed")]
    open_opts = [t for t in trades if not t.get("closed") and t["type"] != "Stock"]

    total_pnl = sum(float(t.get("closed_pnl") or 0) for t in closed)
    total_premium = sum(float(t.get("total_premium") or 0) for t in trades if t["type"] != "Stock")
    open_premium = sum(float(t.get("total_premium") or 0) for t in open_opts)
    wins = sum(1 for t in closed if float(t.get("closed_pnl") or 0) > 0)
    win_rate = f"{wins/len(closed)*100:.0f}%" if closed else "—"
    open_anns = [float(t["annualized"]) for t in open_opts if t.get("annualized")]
    avg_ann = f"{sum(open_anns)/len(open_anns):.1f}%" if open_anns else "—"

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total realized P&L", f"{'+'if total_pnl>=0 else ''}${total_pnl:,.2f}")
    c2.metric("All-time premium", f"${total_premium:,.2f}")
    c3.metric("Open premium at risk", f"${open_premium:,.2f}" if open_premium else "—")
    c4.metric("Win rate", win_rate, f"{wins}/{len(closed)}")
    c5.metric("Avg open ann. return", avg_ann)

    # Monthly premium chart
    st.markdown('<div class="section-title">Monthly premium collected — last 12 months</div>', unsafe_allow_html=True)
    monthly = {}
    for t in trades:
        if t["type"] != "Stock" and t.get("date"):
            key = str(t["date"])[:7]
            monthly[key] = monthly.get(key, 0) + float(t.get("total_premium") or 0)

    months = []
    today = date.today()
    for i in range(11, -1, -1):
        d = date(today.year, today.month, 1) - timedelta(days=i*30)
        key = d.strftime("%Y-%m")
        months.append({"month": d.strftime("%b %y"), "premium": monthly.get(key, 0)})

    df_monthly = pd.DataFrame(months)
    fig = go.Figure(go.Bar(
        x=df_monthly["month"], y=df_monthly["premium"],
        marker_color=["#f0c060" if v > 0 else "#252622" for v in df_monthly["premium"]],
        text=[f"${v:.0f}" if v > 0 else "" for v in df_monthly["premium"]],
        textposition="outside", textfont=dict(size=11, color="#f0c060")
    ))
    fig.update_layout(
        height=220, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=11, color="#7a7a72"), gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(tickfont=dict(size=11, color="#7a7a72"), gridcolor="rgba(255,255,255,0.05)",
                   tickprefix="$"),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # Open positions table
    st.markdown('<div class="section-title">Open positions — projected annualized return</div>', unsafe_allow_html=True)
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
                itm = dist <= 0
                dist_str = "ITM ⚠" if itm else f"+{dist_pct:.1f}% (${abs(dist):.2f})"

            rows.append({
                "Symbol": sym,
                "Type": t["type"],
                "Ann %": f"{ann:.1f}%" if ann else "—",
                "Strike": f"${float(t['strike']):.2f}" if t.get("strike") else "—",
                "Expiry": t.get("expiry", "—"),
                "DTE": f"{dte_left}d" if dte_left is not None else "—",
                "Premium": f"${float(t['total_premium']):.2f}" if t.get("total_premium") else "—",
                "Current $": f"${price:.2f}" if price else "—",
                "% to strike": dist_str,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No open option positions")

    # Per-ticker summary
    st.markdown('<div class="section-title">Per-ticker summary</div>', unsafe_allow_html=True)
    ticker_rows = []
    for sym in tickers:
        sym_trades = [t for t in trades if t["symbol"] == sym]
        sym_closed = [t for t in sym_trades if t.get("closed")]
        sym_open   = [t for t in sym_trades if not t.get("closed") and t["type"] != "Stock"]
        pnl = sum(float(t.get("closed_pnl") or 0) for t in sym_closed)
        op  = sum(float(t.get("total_premium") or 0) for t in sym_open)
        proj = calc_projection(trades, sym)
        cp = fmt_proj(proj["closed_proj"], proj["closed_cycles"], proj["avg_c_dte"], proj["basis"])
        opP= fmt_proj(proj["open_proj"],   proj["open_cycles"],   proj["avg_o_dte"], proj["basis"])
        ticker_rows.append({
            "Ticker": sym,
            "Trades": len(sym_trades),
            "Open": len(sym_open),
            "Open premium": f"${op:.2f}" if op else "—",
            "Realized P&L": f"{'+'if pnl>=0 else ''}${pnl:.2f}",
            "Proj/yr (history)": cp[0],
            "% basis (hist)": cp[1],
            "Proj/yr (open)": opP[0],
            "% basis (open)": opP[1],
        })

    if ticker_rows:
        df_tickers = pd.DataFrame(ticker_rows)
        st.dataframe(df_tickers, use_container_width=True, hide_index=True)

        # Totals
        total_cp  = sum(p["closed_proj"] for sym in tickers for p in [calc_projection(trades, sym)] if p["closed_proj"])
        total_op  = sum(p["open_proj"]   for sym in tickers for p in [calc_projection(trades, sym)] if p["open_proj"])
        total_basis = sum(p["basis"] for sym in tickers for p in [calc_projection(trades, sym)] if p["basis"])
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total realized P&L", f"{'+'if total_pnl>=0 else ''}${total_pnl:,.2f}")
        col2.metric("Total proj/yr (history)", f"${total_cp:,.0f}" if total_cp else "—")
        col3.metric("Total proj/yr (open)", f"${total_op:,.0f}" if total_op else "—")
        if total_basis and total_op:
            col4.metric("Blended yield (open)", f"{total_op/total_basis*100:.1f}%")

# ── Ticker view ────────────────────────────────────────────────────
def render_ticker(sym):
    trades = [t for t in all_trades if t["symbol"] == sym]
    open_trades  = [t for t in trades if not t.get("closed")]
    closed_trades= [t for t in trades if t.get("closed")]
    open_opts    = [t for t in open_trades if t["type"] != "Stock"]

    all_premium  = sum(float(t.get("total_premium") or 0) for t in trades if t["type"] != "Stock")
    closed_pnl   = sum(float(t.get("closed_pnl") or 0) for t in closed_trades)
    open_premium = sum(float(t.get("total_premium") or 0) for t in open_opts)
    wins         = sum(1 for t in closed_trades if float(t.get("closed_pnl") or 0) > 0)
    win_rate     = f"{wins/len(closed_trades)*100:.0f}%" if closed_trades else "—"
    proj         = calc_projection(trades, sym)
    cp           = fmt_proj(proj["closed_proj"], proj["closed_cycles"], proj["avg_c_dte"], proj["basis"])
    opP          = fmt_proj(proj["open_proj"],   proj["open_cycles"],   proj["avg_o_dte"], proj["basis"])

    col_hdr, col_btn, col_btn2 = st.columns([3, 1, 1])
    with col_hdr:
        st.markdown(f"## {sym}")
        st.markdown(f"*{len(trades)} total · {len(open_trades)} open*")
    with col_btn:
        if st.button("+ New trade", type="primary", use_container_width=True):
            st.session_state.show_add_trade = True
            st.session_state.show_quick_add = False
    with col_btn2:
        if st.button("⚡ Quick log", use_container_width=True):
            st.session_state.show_quick_add = True
            st.session_state.show_add_trade = False

    tab1, tab2 = st.tabs(["Trade Log", "⟆ Screener"])

    with tab1:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Realized P&L", f"{'+'if closed_pnl>=0 else ''}${closed_pnl:.2f}")
        c2.metric("All-time premium", f"${all_premium:.2f}")
        c3.metric("Open premium", f"${open_premium:.2f}" if open_premium else "—")
        c4.metric("Win rate", win_rate)
        c5.metric("Proj/yr (history)", cp[0], cp[1])
        c6.metric("Proj/yr (open)", opP[0], opP[1])

        # Open positions
        st.markdown('<div class="section-title">Open positions</div>', unsafe_allow_html=True)
        if open_trades:
            for t in open_trades:
                render_trade_card(t, sym)
        else:
            st.info("No open positions")

        # Closed trades table
        st.markdown('<div class="section-title">Closed trades</div>', unsafe_allow_html=True)
        if closed_trades:
            for t in closed_trades:
                is_opt = t["type"] != "Stock"
                dit = days_between(t["date"], t.get("closed_date", "")) if t.get("closed_date") else "—"
                pnl = float(t.get("closed_pnl") or 0)
                ann = f"{float(t['annualized']):.0f}%" if t.get("annualized") else "—"
                qty_str = f"${float(t['strike']):.0f} strike" if (is_opt and t.get("strike")) else (f"{t.get('shares','')}sh" if t.get("shares") else "")
                label = f"{t['date']} · {t['type']} {t['side']} {qty_str} · ${float(t.get('total_premium',0)):.2f} · P&L: {'+'if pnl>=0 else ''}${pnl:.2f}"
                with st.expander(label):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Type", f"{t['type']} {t['side']}")
                    c2.metric("Total premium", f"${float(t['total_premium']):.2f}")
                    c3.metric("P&L", f"{'+'if pnl>=0 else ''}${pnl:.2f}")
                    c4.metric("DIT", f"{dit}d" if dit != "—" else "—")
                    c5.metric("Ann %", ann)
                    if t.get("notes"):
                        st.caption(f"✎ {t['notes']}")
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
            st.info("No closed trades yet")

    with tab2:
        render_screener(sym, trades)

def render_trade_card(t, sym):
    is_opt = t["type"] != "Stock"
    dit = days_between(t["date"], str(date.today()))
    dte_left = days_between(str(date.today()), t.get("expiry", "")) if t.get("expiry") else None

    with st.container(border=True):
        # Header row
        col_tags, col_date = st.columns([3, 1])
        with col_tags:
            type_color = {"Call": "🔵", "Put": "🟡", "Stock": "⚫"}
            side_color = {"Sell": "🟢", "Buy": "🔴"}
            st.markdown(f"**{type_color.get(t['type'],'')} {t['type']}** &nbsp; {side_color.get(t['side'],'')} {t['side']}")
        with col_date:
            st.caption(t["date"])

        if is_opt:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Strike", f"${float(t['strike']):.2f}")
            c2.metric("Expiry", t.get("expiry", "—"))
            c3.metric("Contracts", t.get("contracts", 1))
            c4.metric("Total premium", f"${float(t['total_premium']):.2f}")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Days to exp", f"{dte_left}d" if dte_left is not None else "—")
            c6.metric("Days held", f"{dit}d")
            ann_str = f"{float(t['annualized']):.1f}%" if t.get("annualized") else "—"
            c7.metric("Proj. annualized", ann_str)

            # If assigned calc for sell calls
            if t["side"] == "Sell" and t["type"] == "Call" and t.get("spot") and t.get("strike"):
                spot = float(t["spot"]); strike = float(t["strike"])
                contracts = int(t.get("contracts", 1))
                total_prem = float(t["total_premium"])
                stock_gain = (strike - spot) * 100 * contracts
                total_profit = stock_gain + total_prem
                raw_pct = total_profit / (spot * 100 * contracts) * 100
                c8.metric("If assigned profit", f"${total_profit:.2f} ({raw_pct:.1f}%)")
            elif t["side"] == "Sell" and t["type"] == "Put" and t.get("spot") and t.get("strike"):
                strike = float(t["strike"]); prem_per_sh = float(t["total_premium"]) / (int(t.get("contracts",1)) * 100)
                be = strike - prem_per_sh
                c8.metric("Breakeven if assigned", f"${be:.2f}/sh")

            # Assignment risk
            if t.get("spot") and t.get("strike") and t["side"] == "Sell":
                spot = float(t["spot"]); strike = float(t["strike"])
                dist = (strike - spot) if t["type"] == "Call" else (spot - strike)
                dist_pct = dist / spot * 100
                sign = "+" if dist >= 0 else ""
                color = "normal" if dist_pct > 10 else ("off" if dist_pct > 4 else "inverse")
                st.metric("Distance to strike", f"{sign}${abs(dist):.2f} ({sign}{dist_pct:.1f}%)", delta_color=color)

            # Breakeven
            if t.get("spot") and t["side"] == "Sell":
                pps = float(t["total_premium"]) / (int(t.get("contracts", 1)) * 100)
                be = float(t["spot"]) - pps if t["type"] == "Call" else float(t["strike"]) - pps
                st.caption(f"Downside breakeven: ${be:.2f}")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Shares", t.get("shares", "—"))
            c2.metric("Buy price", f"${float(t['premium']):.2f}")
            c3.metric("Total cost", f"${float(t['total_premium']):.2f}")
            c4.metric("Days held", f"{dit}d")

        if t.get("notes"):
            st.caption(f"✎ {t['notes']}")

        # Action buttons
        col1, col2, col3, col_space = st.columns([1, 1, 1, 3])
        with col1:
            if st.button("Close", key=f"close_{t['id']}", type="primary"):
                st.session_state[f"closing_{t['id']}"] = True
                st.session_state[f"editing_{t['id']}"] = False
        with col2:
            if st.button("Edit", key=f"edit_{t['id']}"):
                st.session_state[f"editing_{t['id']}"] = True
                st.session_state[f"closing_{t['id']}"] = False
        with col3:
            if st.button("Delete", key=f"del_{t['id']}"):
                delete_trade(t["id"])
                st.rerun()

    if st.session_state.get(f"closing_{t['id']}"):
        render_close_form(t)
    if st.session_state.get(f"editing_{t['id']}"):
        render_edit_form(t)

def render_edit_form(t):
    is_opt = t["type"] != "Stock"
    with st.form(key=f"edit_form_{t['id']}"):
        st.markdown(f"**Edit: {t['symbol']} {t['side']} {t['type']}**")

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
                except: pass
            new_expiry = st.date_input("Expiry", value=exp_val)
            new_spot = st.number_input("Stock price at open ($)", value=float(t.get("spot") or 0), step=0.01)
        else:
            col3, col4 = st.columns(2)
            with col3:
                new_price = st.number_input("Price/share ($)", value=float(t.get("premium") or 0), step=0.01)
            with col4:
                new_shares = st.number_input("Shares", value=int(t.get("shares") or 100), step=1)

        # For quick-logged closed trades — allow editing P&L directly
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
                        ann = (total / (new_spot * 100 * new_contracts)) * (365/dte) * 100
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

def render_close_form(t):
    is_opt = t["type"] != "Stock"
    with st.form(key=f"close_form_{t['id']}"):
        st.markdown(f"**Close: {t['symbol']} {t['side']} {t['type']}**")
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
                st.markdown(f"**Realized P&L: {'+'if pnl>=0 else ''}${pnl:.2f}**")
            else:
                pnl = (close_price - float(t["premium"])) * int(t.get("shares", 100))
                st.markdown(f"**Realized P&L: {'+'if pnl>=0 else ''}${pnl:.2f}**")

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
                    ann = float(t["total_premium"]) / (float(t["spot"]) * 100 * int(t.get("contracts",1))) * (365/dit) * 100

            update_trade(t["id"], {
                "closed": True,
                "closed_date": str(close_date),
                "closed_price": close_price,
                "closed_pnl": round(pnl, 2),
                "annualized": round(ann, 2) if ann else t.get("annualized")
            })
            st.session_state.pop(f"closing_{t['id']}", None)
            st.rerun()

        if cancelled:
            st.session_state.pop(f"closing_{t['id']}", None)
            st.rerun()

# ── Add trade form ─────────────────────────────────────────────────
def render_add_trade_form(sym):
    with st.form("add_trade_form"):
        st.markdown(f"### New trade — {sym}")
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

            # Auto-fill spot from open stock
            open_stock = next((t for t in all_trades if t["symbol"] == sym and t["type"] == "Stock" and t["side"] == "Buy" and not t.get("closed")), None)
            default_spot = float(open_stock["premium"]) if open_stock else 0.0
            with col8:
                spot = st.number_input("Stock price at open ($)", min_value=0.0, value=default_spot, step=0.01,
                                       help="Auto-filled from your open stock position" if open_stock else "Used for annualized return calc")

            if premium > 0:
                total_prem = premium * 100 * contracts
                st.success(f"**Total premium: ${total_prem:.2f}** ({contracts} × 100 × ${premium:.2f})")
                if spot > 0 and expiry:
                    dte = (expiry - trade_date).days
                    if dte > 0:
                        ann = (total_prem / (spot * 100 * contracts)) * (365/dte) * 100
                        st.info(f"**Projected annualized: {ann:.1f}%** · ${total_prem:.2f} ÷ ${spot*100*contracts:.2f} basis × (365÷{dte}d)")

                        if side == "Sell" and strike > 0:
                            if trade_type == "Call":
                                stock_gain = (strike - spot) * 100 * contracts
                                total_profit = stock_gain + total_prem
                                ann_total = (total_profit / (spot * 100 * contracts)) * (365/dte) * 100
                                raw_pct = total_profit / (spot * 100 * contracts) * 100
                                st.warning(f"**If assigned at ${strike}** → Stock gain: {'+'if stock_gain>=0 else ''}${stock_gain:.2f} + ${total_prem:.2f} premium = **${total_profit:.2f} ({raw_pct:.1f}%)** · Annualized: **{ann_total:.1f}%**")
                            elif trade_type == "Put":
                                be = strike - premium
                                raw_pct = total_prem / (spot * 100 * contracts) * 100
                                st.warning(f"**If assigned at ${strike}** → Effective cost: ${be:.2f}/sh · Premium return: {raw_pct:.1f}%")
        else:
            col5, col6 = st.columns(2)
            with col5:
                shares = st.number_input("Shares", min_value=1, value=100, step=1)
            with col6:
                stock_price = st.number_input("Price per share ($)", min_value=0.0, step=0.01)
            if stock_price > 0:
                st.success(f"**Cost basis: ${stock_price * shares:,.2f}** ({shares} shares × ${stock_price:.2f})")

        notes = st.text_input("Notes (optional)", placeholder="e.g. high IV, pre-earnings, wheel trade...")

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
                        ann = (total_prem / (spot * 100 * contracts)) * (365/dte) * 100
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

# ── Screener ───────────────────────────────────────────────────────
def render_screener(sym, trades):
    st.markdown("Fetches live options chain via yfinance · filters 25–55 DTE · ranks by return/safety score")

    open_stock = next((t for t in trades if t["symbol"] == sym and t["type"] == "Stock" and t["side"] == "Buy" and not t.get("closed")), None)
    entry_price = float(open_stock["premium"]) if open_stock else None
    spot = get_price(sym)

    if entry_price:
        st.info(f"Using your entry price **${entry_price:.2f}** for assignment calculations · Current price: **${spot:.2f}**" if spot else f"Using entry **${entry_price:.2f}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        opt_type = st.selectbox("Option type", ["Calls", "Puts"], key="sc_type")
    with col2:
        min_otm = st.number_input("Min OTM %", value=2.0, step=0.5, key="sc_min_otm")
    with col3:
        fetch = st.button("⟆ Fetch chain", type="primary", key="sc_fetch")

    if fetch:
        with st.spinner("Fetching options chain..."):
            df = get_options_chain(sym, opt_type.lower()[:-1] + "s")

        if df.empty:
            st.error("No contracts found — check ticker or try different DTE range")
            return

        basis = (entry_price or spot or 1) * 100
        results = []
        for _, row in df.iterrows():
            strike = float(row.get("strike", 0))
            bid    = float(row.get("bid", 0) or 0)
            ask    = float(row.get("ask", 0) or 0)
            mid    = (bid + ask) / 2
            dte    = int(row.get("dte", 30))
            expiry = str(row.get("expiry", ""))
            iv     = float(row.get("impliedVolatility", 0) or 0)
            if mid <= 0 or strike <= 0: continue

            if spot:
                otm = ((strike - spot) / spot * 100) if opt_type == "Calls" else ((spot - strike) / spot * 100)
            else:
                otm = 0
            if otm < min_otm: continue

            total_prem = mid * 100
            ann_return = (total_prem / basis) * (365 / dte) * 100 if dte > 0 else 0

            assigned_str = "—"
            if opt_type == "Calls" and entry_price:
                stock_gain = (strike - entry_price) * 100
                total_profit = stock_gain + total_prem
                ann_total = (total_profit / (entry_price * 100)) * (365 / dte) * 100 if dte > 0 else 0
                raw_pct = total_profit / (entry_price * 100) * 100
                assigned_str = f"${total_profit:.0f} ({raw_pct:.1f}% · {ann_total:.0f}% ann)"
            elif opt_type == "Puts":
                be = strike - mid
                assigned_str = f"Breakeven ${be:.2f}"

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
                "IV": f"{iv*100:.0f}%" if iv else "—",
                "_score": score
            })

        if not results:
            st.warning("No contracts passed filters — try lowering Min OTM %")
            return

        results.sort(key=lambda x: x["_score"], reverse=True)
        for r in results:
            del r["_score"]

        df_res = pd.DataFrame(results[:30])
        st.markdown(f"*{len(results)} contracts found · showing top {min(30,len(results))} by score · Score = 60% return + 40% OTM safety*")
        st.dataframe(df_res, use_container_width=True, hide_index=True)

# ── Quick log form ─────────────────────────────────────────────────
def render_quick_add(sym):
    with st.form("quick_add_form"):
        st.markdown(f"### ⚡ Quick log — {sym}")
        st.caption("Log a already-closed trade in one step")

        col1, col2, col3 = st.columns(3)
        with col1:
            trade_type = st.selectbox("Type", ["Call", "Put", "Stock"])
        with col2:
            side = st.selectbox("Side", ["Sell", "Buy"])
        with col3:
            trade_date = st.date_input("Trade date", value=date.today())

        col4, col5, col6 = st.columns(3)
        with col4:
            total_premium = st.number_input("Premium collected ($)", min_value=0.0, step=1.0,
                                             help="Total $ received e.g. $63")
        with col5:
            realized_pnl = st.number_input("Realized P&L ($)", step=1.0,
                                            help="Profit or loss. Positive = profit, negative = loss")
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
