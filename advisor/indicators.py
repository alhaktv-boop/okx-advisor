from typing import List

def ema(values: List[float], n: int) -> List[float]:
    k, out, prev = 2 / (n + 1), [], None
    for v in values:
        prev = v if prev is None else v * k + prev * (1 - k)
        out.append(prev)
    return out

def rsi(closes: List[float], n: int = 14) -> List[float]:
    out, g, l = [50.0] * len(closes), 0.0, 0.0
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        up, dn = max(d, 0), max(-d, 0)
        if i <= n:
            g += up / n; l += dn / n
        else:
            g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n
        out[i] = 100.0 if l == 0 else 100 - 100 / (1 + g / l)
    return out

def atr(h, l, c, n: int = 14) -> List[float]:
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1])) for i in range(1, len(c))]
    out, prev = [], None
    for i, t in enumerate(tr):
        prev = t if prev is None else (prev * (n - 1) + t) / n
        out.append(prev)
    return out
