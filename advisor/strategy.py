"""Rule-based entry signal: buy pullbacks inside an uptrend. Long-only (spot)."""
from .indicators import ema, rsi, atr
from .config import Config

def signal(candles, cfg: Config):
    """candles: list of dicts with o,h,l,c,v (oldest first, last one CLOSED).
    Returns None or dict(entry, stop, target, why)."""
    if len(candles) < 220:
        return None
    h = [x["h"] for x in candles]; l = [x["l"] for x in candles]; c = [x["c"] for x in candles]
    e50, e200, r, a = ema(c, 50), ema(c, 200), rsi(c), atr(h, l, c)
    i = len(c) - 1
    trend_up = c[i] > e200[i] and e50[i] > e200[i]
    pullback = r[i - 1] < 35 and r[i] > r[i - 1] and r[i] < 50   # RSI turning up from oversold
    if not (trend_up and pullback):
        return None
    entry = c[i]
    stop = entry - cfg.stop_atr * a[i]
    target = entry + cfg.target_atr * a[i]
    if (target - entry) / entry < cfg.min_edge_pct:
        return None                       # move too small: fees would eat it
    strength = ((e50[i] - e200[i]) / e200[i]) / (a[i] / entry)   # trend strength per unit of volatility
    return {"score": strength, "entry": entry, "stop": stop, "target": target,
            "why": f"uptrend (EMA50>EMA200), RSI {r[i-1]:.0f}->{r[i]:.0f}, ATR {a[i]:.2f}"}
