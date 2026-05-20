import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

from data import fetch_history, fetch_batch
from analysis import analyze_stock, SIGNAL_LABELS

st.set_page_config(
    page_title="VN Stock Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

.metric-card {
    background: #0f1117;
    border: 1px solid #1e2130;
    border-radius: 8px;
    padding: 16px 20px;
    text-align: center;
}
.metric-val { font-size: 28px; font-weight: 500; font-family: 'IBM Plex Mono', monospace; }
.metric-label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 4px; }

.pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    font-family: 'IBM Plex Mono', monospace;
}
.pill-buy { background: #0d2b1a; color: #3ddc84; border: 1px solid #1a5c38; }
.pill-avoid { background: #2b0d0d; color: #ff6b6b; border: 1px solid #5c1a1a; }
.pill-watch { background: #2b1f0d; color: #ffb347; border: 1px solid #5c3d1a; }
.pill-pump { background: #2b1a0d; color: #ff9f43; border: 1px solid #5c3010; }
.pill-surf { background: #0d1b2b; color: #54a0ff; border: 1px solid #1a3c5c; }

.section-header {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #555;
    border-bottom: 1px solid #1e2130;
    padding-bottom: 6px;
    margin-bottom: 12px;
}

.rec-box {
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 14px;
    line-height: 1.6;
}
.rec-buy { background: #0d2b1a; border-left: 3px solid #3ddc84; color: #3ddc84; }
.rec-avoid { background: #2b0d0d; border-left: 3px solid #ff6b6b; color: #ff6b6b; }
.rec-watch { background: #2b1f0d; border-left: 3px solid #ffb347; color: #ffb347; }
.rec-surf { background: #0d1b2b; border-left: 3px solid #54a0ff; color: #54a0ff; }

.pump-alert {
    background: #2b1a0d;
    border: 1px solid #5c3010;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0;
}
.surf-card {
    background: #0d1b2b;
    border: 1px solid #1a3c5c;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0;
}

[data-testid="stDataFrame"] { font-family: 'IBM Plex Mono', monospace; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

PRESETS = {
    "VN30 Blue-chip": ["VIC","VHM","VCB","BID","CTG","HPG","GAS","SAB","MSN","TCB","MBB","VPB","ACB","HDB","FPT"],
    "Ngân hàng": ["VCB","BID","CTG","TCB","MBB","VPB","ACB","HDB","STB","LPB","OCB","SSB"],
    "Thép & Vật liệu": ["HPG","HSG","NKG","TVN","POM","TLH","SMC","VGS"],
    "Bất động sản": ["VIC","VHM","NVL","PDR","KDH","NLG","DXG","VRE","SCR","DIG"],
    "Công nghệ": ["FPT","CMG","VGI","ELC","ITD","SAM"],
    "Tiêu dùng & Bán lẻ": ["VNM","SAB","MWG","PNJ","MSN","BAF","QNS"],
}

if "watchlist" not in st.session_state:
    st.session_state.watchlist = list(PRESETS["VN30 Blue-chip"])
if "data_cache" not in st.session_state:
    st.session_state.data_cache = {}
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None

with st.sidebar:
    st.markdown("## 📈 VN Stock Intel")
    st.markdown('<div class="section-header">Danh mục theo dõi</div>', unsafe_allow_html=True)

    preset = st.selectbox("Chọn nhóm ngành", list(PRESETS.keys()), label_visibility="collapsed")
    if st.button("Tải preset", use_container_width=True):
        st.session_state.watchlist = list(PRESETS[preset])
        st.session_state.data_cache = {}
        st.rerun()

    st.markdown("---")
    new_ticker = st.text_input("Thêm mã thủ công", placeholder="VD: VIC, HPG...").upper().strip()
    if st.button("+ Thêm vào danh sách", use_container_width=True):
        tickers = [t.strip() for t in new_ticker.split(",") if t.strip()]
        for t in tickers:
            if t and t not in st.session_state.watchlist:
                st.session_state.watchlist.append(t)
        st.session_state.data_cache = {}
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-header">Danh sách hiện tại</div>', unsafe_allow_html=True)
    to_remove = []
    cols_per_row = 3
    tickers = st.session_state.watchlist
    for i in range(0, len(tickers), cols_per_row):
        row_tickers = tickers[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for j, t in enumerate(row_tickers):
            with cols[j]:
                if st.button(t, key=f"rm_{t}", help=f"Click để xoá {t}"):
                    to_remove.append(t)
    if to_remove:
        for t in to_remove:
            st.session_state.watchlist.remove(t)
        st.rerun()

    st.markdown("---")
    days_back = st.slider("Lịch sử (ngày)", 30, 180, 60)
    if st.button("🔄 Làm mới dữ liệu", use_container_width=True, type="primary"):
        st.session_state.data_cache = {}
        st.rerun()

# ── Main area ──────────────────────────────────────────────────────────────
st.markdown("## Vietnam Stock Intelligence Dashboard")
st.markdown(f"*Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')} · {len(st.session_state.watchlist)} mã đang theo dõi*")

# Load data
cache = st.session_state.data_cache
missing = [t for t in st.session_state.watchlist if t not in cache]

if missing:
    prog = st.progress(0, text=f"Đang tải {len(missing)} mã...")
    results = fetch_batch(missing, days_back=days_back, progress_cb=lambda i, n, t: prog.progress(i/n, text=f"Đang tải {t}... ({i}/{n})"))
    cache.update(results)
    st.session_state.data_cache = cache
    prog.empty()

# Analyze all
analyses = {}
for t in st.session_state.watchlist:
    if t in cache and cache[t] is not None:
        analyses[t] = analyze_stock(cache[t])

buy_count  = sum(1 for a in analyses.values() if a["signal"] == "buy")
pump_count = sum(1 for a in analyses.values() if a["pump_score"] >= 50)
surf_count = sum(1 for a in analyses.values() if a["surf"])
fail_count = len(st.session_state.watchlist) - len(analyses)

# ── Metric row ────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Đang theo dõi", len(st.session_state.watchlist))
with c2:
    st.metric("Tín hiệu MUA", buy_count, delta=None)
with c3:
    st.metric("Pump Alert", pump_count)
with c4:
    st.metric("Lướt sóng T+", surf_count)
with c5:
    st.metric("Lỗi tải", fail_count)

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Tổng quan", "🚨 Pump Detector", "🏄 Lướt sóng", "🔍 Chi tiết cổ phiếu"])

# ─────────────────────────────────────────────────────────────────
# TAB 1 — Overview table
# ─────────────────────────────────────────────────────────────────
with tab1:
    rows = []
    for t in st.session_state.watchlist:
        if t not in analyses:
            rows.append({"Mã CP": t, "Giá (VNĐ)": None, "+/- ngày": None, "Pump Score": 0, "Tín hiệu": "N/A", "Lướt sóng": False})
            continue
        a = analyses[t]
        rows.append({
            "Mã CP": t,
            "Giá (VNĐ)": a["last_price"],
            "+/- ngày (%)": round(a["chg_1d"], 2),
            "Pump Score": a["pump_score"],
            "MA5": round(a["ma5"], 0) if a["ma5"] else None,
            "MA20": round(a["ma20"], 0) if a["ma20"] else None,
            "Tín hiệu": SIGNAL_LABELS[a["signal"]],
            "Lướt sóng": "✓" if a["surf"] else "",
        })

    df = pd.DataFrame(rows)

    def color_signal(val):
        if "MUA" in str(val): return "color: #3ddc84; font-weight: 500"
        if "TRÁNH" in str(val): return "color: #ff6b6b; font-weight: 500"
        if "THEO DÕI" in str(val): return "color: #ffb347"
        return ""
    def color_chg(val):
        try:
            v = float(val)
            return "color: #3ddc84" if v >= 0 else "color: #ff6b6b"
        except: return ""
    def color_pump(val):
        try:
            v = int(val)
            if v >= 70: return "color: #ff6b6b; font-weight: 500"
            if v >= 40: return "color: #ffb347"
            return "color: #3ddc84"
        except: return ""

    styled = df.style\
        .map(color_signal, subset=["Tín hiệu"])\
        .map(color_chg, subset=["+/- ngày (%)"])\
        .map(color_pump, subset=["Pump Score"])\
        .format({"Giá (VNĐ)": "{:,.0f}", "MA5": "{:,.0f}", "MA20": "{:,.0f}"}, na_rep="—")

    st.dataframe(styled, use_container_width=True, height=500)

    st.markdown("*Nhấn tab **Chi tiết cổ phiếu** để xem biểu đồ và phân tích kỹ thuật từng mã.*")

# ─────────────────────────────────────────────────────────────────
# TAB 2 — Pump Detector
# ─────────────────────────────────────────────────────────────────
with tab2:
    st.markdown("#### Phát hiện cổ phiếu có dấu hiệu thổi giá bất thường")
    st.caption("Dựa trên: khối lượng đột biến so với trung bình, tốc độ tăng giá bất thường trong 3–10 phiên, và thanh khoản mỏng.")

    pump_items = [(t, analyses[t]) for t in st.session_state.watchlist if t in analyses and analyses[t]["pump_score"] >= 30]
    pump_items.sort(key=lambda x: -x[1]["pump_score"])

    if not pump_items:
        st.success("✅ Không phát hiện cổ phiếu nào có dấu hiệu pump bất thường trong danh sách hiện tại.")
    else:
        for t, a in pump_items:
            score = a["pump_score"]
            lvl = "🔴 Nguy hiểm cao" if score >= 70 else "🟠 Nghi ngờ pump" if score >= 50 else "🟡 Chú ý"
            col1, col2, col3 = st.columns([2, 6, 2])
            with col1:
                st.markdown(f"### {t}")
                st.caption(f"{a['last_price']:,.0f} VNĐ" if a['last_price'] else "—")
            with col2:
                sigs = a.get("pump_signals", [])
                if sigs:
                    for s in sigs:
                        st.markdown(f"- {s}")
                else:
                    st.caption("Không có tín hiệu chi tiết")
            with col3:
                color = "#ff6b6b" if score >= 70 else "#ffb347" if score >= 50 else "#ffd700"
                st.markdown(f"<div style='text-align:center;font-size:32px;font-weight:500;color:{color};font-family:IBM Plex Mono'>{score}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;font-size:11px;color:{color}'>{lvl}</div>", unsafe_allow_html=True)
            st.markdown("---")

# ─────────────────────────────────────────────────────────────────
# TAB 3 — Surf opportunities
# ─────────────────────────────────────────────────────────────────
with tab3:
    st.markdown("#### Cơ hội lướt sóng ngắn hạn T+2/T+3")
    st.caption("Điều kiện: Momentum tăng xác nhận · Volume hỗ trợ · Pump score < 50 · MA5 > MA10")

    surf_items = [(t, analyses[t]) for t in st.session_state.watchlist if t in analyses and analyses[t]["surf"]]

    if not surf_items:
        st.info("Hiện chưa có cổ phiếu nào trong danh sách đủ điều kiện lướt sóng.")
    else:
        surf_df_rows = []
        for t, a in surf_items:
            lp = a["last_price"] or 0
            surf_df_rows.append({
                "Mã CP": t,
                "Giá hiện tại": lp,
                "Mục tiêu (+5%)": round(lp * 1.05),
                "Cắt lỗ (-3%)": round(lp * 0.97),
                "Tỷ lệ R:R": "1.67x",
                "Khung T+": "T+2 / T+3",
                "Lý do": a.get("surf_reason", "Momentum + volume xác nhận"),
            })
        surf_df = pd.DataFrame(surf_df_rows)
        st.dataframe(
            surf_df.style.format({"Giá hiện tại": "{:,.0f}", "Mục tiêu (+5%)": "{:,.0f}", "Cắt lỗ (-3%)": "{:,.0f}"}),
            use_container_width=True
        )
        st.warning("⚠️ Đây là công cụ hỗ trợ phân tích kỹ thuật, không phải lời khuyên đầu tư. Anh tự chịu trách nhiệm với quyết định của mình.")

# ─────────────────────────────────────────────────────────────────
# TAB 4 — Detail view
# ─────────────────────────────────────────────────────────────────
with tab4:
    available = [t for t in st.session_state.watchlist if t in analyses]
    if not available:
        st.info("Chưa có dữ liệu. Nhấn 'Làm mới dữ liệu' ở sidebar.")
    else:
        selected = st.selectbox("Chọn mã cổ phiếu", available)
        if selected:
            a = analyses[selected]
            df_hist = cache[selected]

            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Giá đóng cửa", f"{a['last_price']:,.0f}" if a['last_price'] else "—", delta=f"{a['chg_1d']:+.2f}%" if a['chg_1d'] is not None else None)
            with col2: st.metric("MA5", f"{a['ma5']:,.0f}" if a['ma5'] else "—")
            with col3: st.metric("MA20", f"{a['ma20']:,.0f}" if a['ma20'] else "—")
            with col4: st.metric("Pump Score", a['pump_score'])

            sig = a["signal"]
            sig_label = SIGNAL_LABELS[sig]
            rec_reason = a.get("reason", "")
            if a["surf"]:
                st.markdown(f'<div class="rec-box rec-surf">↗ <strong>Phù hợp lướt sóng T+2/T+3</strong><br>{rec_reason}</div>', unsafe_allow_html=True)
            elif sig == "buy":
                st.markdown(f'<div class="rec-box rec-buy">● <strong>Khuyến nghị MUA</strong><br>{rec_reason}</div>', unsafe_allow_html=True)
            elif sig == "avoid":
                st.markdown(f'<div class="rec-box rec-avoid">✗ <strong>Khuyến nghị TRÁNH</strong><br>{rec_reason}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="rec-box rec-watch">~ <strong>Theo dõi thêm</strong><br>{rec_reason}</div>', unsafe_allow_html=True)

            if a["pump_score"] >= 50:
                st.markdown(f'<div style="margin-top:8px;padding:10px 14px;background:#2b1a0d;border:1px solid #5c3010;border-radius:8px;color:#ff9f43;font-size:13px">⚠️ <strong>Pump Score {a["pump_score"]}/100</strong> — Giá có thể đã bị đẩy lên bất thường. Cẩn trọng rủi ro.</div>', unsafe_allow_html=True)

            st.markdown("---")

            # Price + volume chart
            df_plot = df_hist.tail(60).copy()
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df_plot["date"], open=df_plot["open"], high=df_plot["high"],
                low=df_plot["low"], close=df_plot["close"],
                name="Giá", increasing_line_color="#3ddc84", decreasing_line_color="#ff6b6b",
                increasing_fillcolor="#3ddc84", decreasing_fillcolor="#ff6b6b"
            ), row=1, col=1)

            # MA lines
            if len(df_plot) >= 5:
                df_plot["MA5"] = df_plot["close"].rolling(5).mean()
                fig.add_trace(go.Scatter(x=df_plot["date"], y=df_plot["MA5"], name="MA5", line=dict(color="#54a0ff", width=1.5), opacity=0.9), row=1, col=1)
            if len(df_plot) >= 20:
                df_plot["MA20"] = df_plot["close"].rolling(20).mean()
                fig.add_trace(go.Scatter(x=df_plot["date"], y=df_plot["MA20"], name="MA20", line=dict(color="#ffb347", width=1.5, dash="dot"), opacity=0.9), row=1, col=1)

            # Volume bars
            colors = ["#3ddc84" if c >= o else "#ff6b6b" for c, o in zip(df_plot["close"], df_plot["open"])]
            fig.add_trace(go.Bar(x=df_plot["date"], y=df_plot["volume"], name="Khối lượng", marker_color=colors, opacity=0.7), row=2, col=1)

            fig.update_layout(
                template="plotly_dark", paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                height=480, margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", y=1.02, x=0),
                xaxis_rangeslider_visible=False,
                font=dict(family="IBM Plex Mono", size=11)
            )
            fig.update_xaxes(showgrid=False, gridcolor="#1e2130")
            fig.update_yaxes(gridcolor="#1e2130", showgrid=True)
            st.plotly_chart(fig, use_container_width=True)

            # Technical signals detail
            st.markdown("#### Tín hiệu kỹ thuật chi tiết")
            sigs = a.get("signals", [])
            if sigs:
                sc1, sc2 = st.columns(2)
                for i, s in enumerate(sigs):
                    col = sc1 if i % 2 == 0 else sc2
                    icon = "✅" if s["good"] else "❌" if s["bad"] else "⚠️"
                    col.markdown(f"{icon} **{s['label']}** — {s['value']}")
