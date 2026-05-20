"""
analysis.py — Phân tích kỹ thuật: pump detection, buy signal, lướt sóng
"""
import pandas as pd
import numpy as np
from typing import Optional

SIGNAL_LABELS = {
    "buy":   "✅ MUA",
    "watch": "👀 THEO DÕI",
    "avoid": "🚫 TRÁNH",
}


def _ma(series: pd.Series, n: int) -> Optional[float]:
    if len(series) < n:
        return None
    return float(series.iloc[-n:].mean())


def _rsi(series: pd.Series, period: int = 14) -> Optional[float]:
    if len(series) < period + 1:
        return None
    delta = series.diff().dropna()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.rolling(period).mean().iloc[-1]
    avg_loss = loss.rolling(period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _vol_ratio(volumes: pd.Series, lookback: int = 10) -> float:
    """Tỷ lệ volume phiên cuối so với TB {lookback} phiên trước."""
    if len(volumes) < lookback + 1:
        return 1.0
    avg = float(volumes.iloc[-(lookback+1):-1].mean())
    last = float(volumes.iloc[-1])
    return (last / avg) if avg > 0 else 1.0


def analyze_stock(df: pd.DataFrame) -> dict:
    """
    Phân tích một cổ phiếu.

    Trả về dict:
      last_price, chg_1d, ma5, ma10, ma20, rsi
      pump_score (0–100), pump_signals [str]
      signal ("buy"|"watch"|"avoid"), reason, signals [{"label","value","good","bad"}]
      surf (bool), surf_reason (str)
    """
    result = {
        "last_price": None, "chg_1d": None,
        "ma5": None, "ma10": None, "ma20": None, "rsi": None,
        "pump_score": 0, "pump_signals": [],
        "signal": "watch", "reason": "Không đủ dữ liệu", "signals": [],
        "surf": False, "surf_reason": "",
    }

    if df is None or len(df) < 5:
        return result

    closes  = df["close"]
    volumes = df["volume"]
    opens   = df["open"]

    last  = float(closes.iloc[-1])
    prev  = float(closes.iloc[-2]) if len(closes) >= 2 else last
    chg1d = ((last - prev) / prev * 100) if prev > 0 else 0.0

    ma5  = _ma(closes, 5)
    ma10 = _ma(closes, 10)
    ma20 = _ma(closes, 20)
    rsi  = _rsi(closes)

    result.update({"last_price": last, "chg_1d": round(chg1d, 2), "ma5": ma5, "ma10": ma10, "ma20": ma20, "rsi": rsi})

    # ── Pump detection ────────────────────────────────────────────────────
    pump_score  = 0
    pump_signals = []

    vol_ratio = _vol_ratio(volumes, 10)
    if vol_ratio > 4:
        pump_score += 40
        pump_signals.append(f"🔴 Volume đột biến cực mạnh: +{vol_ratio:.1f}x so với TB 10 phiên")
    elif vol_ratio > 2.5:
        pump_score += 25
        pump_signals.append(f"🟠 Volume tăng đột biến: +{vol_ratio:.1f}x so với TB 10 phiên")
    elif vol_ratio > 1.8:
        pump_score += 12
        pump_signals.append(f"🟡 Volume cao hơn bình thường: +{vol_ratio:.1f}x")

    chg3d  = ((last - float(closes.iloc[-4])) / float(closes.iloc[-4]) * 100) if len(closes) >= 4 else 0
    chg5d  = ((last - float(closes.iloc[-6])) / float(closes.iloc[-6]) * 100) if len(closes) >= 6 else 0
    chg10d = ((last - float(closes.iloc[-11])) / float(closes.iloc[-11]) * 100) if len(closes) >= 11 else 0

    if chg3d > 20:
        pump_score += 35
        pump_signals.append(f"🔴 Tăng {chg3d:.1f}% trong 3 phiên — tốc độ bất thường")
    elif chg3d > 12:
        pump_score += 22
        pump_signals.append(f"🟠 Tăng {chg3d:.1f}% trong 3 phiên")
    elif chg3d > 7:
        pump_score += 10
        pump_signals.append(f"🟡 Tăng {chg3d:.1f}% trong 3 phiên")

    if chg10d > 40:
        pump_score += 25
        pump_signals.append(f"🔴 Tăng {chg10d:.1f}% trong 10 phiên — rủi ro điều chỉnh cao")
    elif chg10d > 25:
        pump_score += 15
        pump_signals.append(f"🟠 Tăng {chg10d:.1f}% trong 10 phiên")

    # RSI overbought
    if rsi and rsi > 80:
        pump_score += 20
        pump_signals.append(f"🔴 RSI = {rsi:.1f} — vùng quá mua cực mạnh")
    elif rsi and rsi > 70:
        pump_score += 10
        pump_signals.append(f"🟠 RSI = {rsi:.1f} — vùng quá mua")

    pump_score = min(pump_score, 100)
    result["pump_score"]   = pump_score
    result["pump_signals"] = pump_signals

    # ── Buy/Avoid signal ──────────────────────────────────────────────────
    bull  = 0
    bear  = 0
    signals = []

    def sig(label, value, is_good: bool):
        signals.append({"label": label, "value": value, "good": is_good, "bad": not is_good})
        return is_good

    vol_ok = vol_ratio >= 1.1
    if vol_ok:
        bull += 1
        sig("Volume xác nhận", f"+{vol_ratio:.1f}x", True)
    else:
        sig("Volume thấp/trung bình", f"{vol_ratio:.1f}x", False)

    if ma5 and last > ma5:
        bull += 1
        sig("Giá > MA5", f"{last:,.0f} > {ma5:,.0f}", True)
    elif ma5:
        bear += 1
        sig("Giá < MA5", f"{last:,.0f} < {ma5:,.0f}", False)

    if ma5 and ma10:
        if ma5 > ma10:
            bull += 1
            sig("MA5 > MA10 (uptrend)", f"{ma5:,.0f} > {ma10:,.0f}", True)
        else:
            bear += 1
            sig("MA5 < MA10 (downtrend)", f"{ma5:,.0f} < {ma10:,.0f}", False)

    if ma20 and last > ma20:
        bull += 1
        sig("Giá > MA20", f"{last:,.0f} > {ma20:,.0f}", True)
    elif ma20:
        bear += 1
        sig("Giá < MA20", f"{last:,.0f} < {ma20:,.0f}", False)

    if rsi:
        if 40 <= rsi <= 65:
            bull += 1
            sig("RSI vùng tốt", f"{rsi:.1f}", True)
        elif rsi > 70:
            bear += 1
            sig("RSI overbought", f"{rsi:.1f}", False)
        elif rsi < 30:
            sig("RSI oversold — có thể bật", f"{rsi:.1f}", True)
        else:
            sig("RSI trung lập", f"{rsi:.1f}", True)

    sig("Thay đổi hôm nay", f"{chg1d:+.2f}%", chg1d >= 0)
    if len(closes) >= 4:
        sig("Thay đổi 3 phiên", f"{chg3d:+.1f}%", chg3d >= 0)

    # Quyết định
    if bull >= 4 and vol_ok and pump_score < 50:
        signal  = "buy"
        reason  = f"Xu hướng tăng rõ ràng với {bull} tín hiệu tích cực, volume xác nhận. Phù hợp tích lũy hoặc lướt sóng ngắn hạn."
    elif bull >= 3 and bear <= 1:
        signal  = "buy"
        reason  = f"{bull} tín hiệu tích cực. Có thể theo dõi điểm vào hợp lý."
    elif bear >= 3:
        signal  = "avoid"
        reason  = f"{bear} tín hiệu tiêu cực. Xu hướng giảm hoặc sideway — chờ tín hiệu đảo chiều rõ hơn."
    else:
        signal  = "watch"
        reason  = f"Tín hiệu hỗn hợp ({bull} tích cực, {bear} tiêu cực). Theo dõi thêm 1–2 phiên để xác nhận."

    if pump_score >= 60:
        reason += f" ⚠️ Pump score cao ({pump_score}/100) — rủi ro điều chỉnh mạnh."

    result["signal"]  = signal
    result["reason"]  = reason
    result["signals"] = signals

    # ── Surf recommendation ───────────────────────────────────────────────
    surf = (
        signal in ("buy",)
        and pump_score < 50
        and vol_ok
        and (ma5 is None or last > ma5)
        and (rsi is None or rsi < 70)
    )
    surf_reason = ""
    if surf:
        surf_reason = f"Momentum tăng ({bull} tín hiệu), volume +{vol_ratio:.1f}x, pump score {pump_score}/100 — rủi ro thấp. Target +5%, cắt lỗ -3%."

    result["surf"]        = surf
    result["surf_reason"] = surf_reason

    return result
