"""
data.py — Lấy dữ liệu chứng khoán qua vnstock (TCBS + VCI)
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ── vnstock import với fallback ────────────────────────────────────────────
try:
    from vnstock import Quote
    VNSTOCK_OK = True
    log.info("vnstock loaded OK")
except ImportError:
    VNSTOCK_OK = False
    log.warning("vnstock not installed — dùng fallback HTTP")

# ── Fallback: direct HTTP (nếu vnstock chưa cài) ──────────────────────────
import requests
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
})

REQUIRED_COLS = {"date", "open", "high", "low", "close", "volume"}

def _normalize(df: pd.DataFrame) -> pd.DataFrame | None:
    """Chuẩn hoá cột về format chung."""
    if df is None or df.empty:
        return None
    df = df.copy()
    # Rename common variants
    rename = {
        "tradingDate": "date", "time": "date",
        "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume",
        "nmVolume": "volume", "matchVolume": "volume",
    }
    df.rename(columns={k: v for k, v in rename.items() if k in df.columns}, inplace=True)
    if not REQUIRED_COLS.issubset(df.columns):
        return None
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "close"])
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df = df[df["close"] > 0]
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df[["date","open","high","low","close","volume"]]


def _fetch_vnstock(ticker: str, days_back: int = 60) -> pd.DataFrame | None:
    """Lấy dữ liệu qua thư viện vnstock."""
    if not VNSTOCK_OK:
        return None
    try:
        end = datetime.today().strftime("%Y-%m-%d")
        start = (datetime.today() - timedelta(days=days_back + 10)).strftime("%Y-%m-%d")
        # Thử TCBS trước, nếu lỗi thử VCI
        for source in ("TCBS", "VCI"):
            try:
                q = Quote(symbol=ticker, source=source)
                df = q.history(start=start, end=end, interval="1D")
                result = _normalize(df)
                if result is not None and len(result) >= 5:
                    log.info(f"{ticker}: OK via vnstock/{source} ({len(result)} rows)")
                    return result
            except Exception as e:
                log.debug(f"{ticker}/{source}: {e}")
        return None
    except Exception as e:
        log.warning(f"{ticker} vnstock error: {e}")
        return None


def _fetch_http_tcbs(ticker: str, days_back: int = 60) -> pd.DataFrame | None:
    """Fallback: gọi thẳng TCBS API."""
    try:
        to_ts  = int(time.time())
        from_ts = to_ts - 86400 * (days_back + 10)
        url = f"https://apipubaws.tcbs.com.vn/stock-insight/v2/stock/bars-long-term?ticker={ticker}&type=stock&resolution=D&from={from_ts}&to={to_ts}"
        r = SESSION.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get("data") or []
        if not data:
            return None
        df = pd.DataFrame(data)
        # TCBS v2 columns: tradingDate, open, high, low, close, volume
        if "tradingDate" not in df.columns and "time" in df.columns:
            df["tradingDate"] = pd.to_datetime(df["time"], unit="s")
        return _normalize(df)
    except Exception as e:
        log.warning(f"{ticker} TCBS HTTP: {e}")
        return None


def _fetch_http_vndirect(ticker: str, days_back: int = 60) -> pd.DataFrame | None:
    """Fallback: VNDirect finfo API."""
    try:
        end   = datetime.today().strftime("%Y-%m-%d")
        start = (datetime.today() - timedelta(days=days_back + 10)).strftime("%Y-%m-%d")
        url = (f"https://finfo-api.vndirect.com.vn/v4/stock_prices"
               f"?code={ticker}&fromDate={start}&toDate={end}&sort=date&size=200")
        r = SESSION.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get("data") or []
        if not data:
            return None
        return _normalize(pd.DataFrame(data))
    except Exception as e:
        log.warning(f"{ticker} VNDirect: {e}")
        return None


def fetch_history(ticker: str, days_back: int = 60) -> pd.DataFrame | None:
    """
    Lấy lịch sử giá cổ phiếu. Thứ tự ưu tiên:
      1. vnstock (TCBS → VCI)
      2. HTTP TCBS trực tiếp
      3. HTTP VNDirect
    Trả về DataFrame với cột: date, open, high, low, close, volume
    Trả về None nếu tất cả đều thất bại.
    """
    result = _fetch_vnstock(ticker, days_back)
    if result is not None:
        return result.tail(days_back)

    result = _fetch_http_tcbs(ticker, days_back)
    if result is not None:
        return result.tail(days_back)

    result = _fetch_http_vndirect(ticker, days_back)
    if result is not None:
        return result.tail(days_back)

    log.error(f"{ticker}: Tất cả nguồn đều thất bại")
    return None


def fetch_batch(tickers: list[str], days_back: int = 60, progress_cb=None) -> dict:
    """
    Lấy dữ liệu cho nhiều mã.
    progress_cb(i, total, ticker) — callback hiển thị tiến trình.
    """
    results = {}
    for i, ticker in enumerate(tickers, 1):
        if progress_cb:
            progress_cb(i, len(tickers), ticker)
        results[ticker] = fetch_history(ticker, days_back)
        time.sleep(0.15)  # gentle rate limit
    return results
