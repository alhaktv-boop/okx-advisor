"""Study v3: how professional trend followers (CTAs) trade, applied to crypto spot (long/cash only).
Pro ingredients: (1) trend signals over several horizons, (2) position size inversely proportional to volatility
(volatility targeting), (3) cut a position the moment its trend breaks, (4) diversify across coins.
All variants are FIXED in advance and reported with a first-half / second-half split."""
import os, math, datetime
from dataclasses import replace
from .config import Config
from .backtest import history
from .live import notify
from .daily import run, metrics, sma, momentum, hold_btc, table
from .daily_v2 import momentum_v2, halves

def vol(x, i, n=30):
    r = [math.log(x[k] / x[k - 1]) for k in range(i - n + 1, i + 1)]
    mu = sum(r) / n
    return max(0.3, math.sqrt(sum((v - mu) ** 2 for v in r) / n) * math.sqrt(365))

def sig_sma(n):
    return lambda i, C, c, st: 1.0 if C[c][i] > sma(C[c], n, i) else 0.0

def sig_multi(hs=(20, 50, 100, 200)):
    return lambda i, C, c, st: sum(C[c][i] > sma(C[c], h, i) for h in hs) / len(hs)

def sig_turtle(n_in=55, n_out=20):
    def f(i, C, c, st):
        held = st.setdefault("turtle", {})
        x = C[c]
        if not held.get(c) and x[i] > max(x[i - n_in:i]): held[c] = True
        elif held.get(c) and x[i] < min(x[i - n_out:i]): held[c] = False
        return 1.0 if held.get(c) else 0.0
    return f

def vt(signal, T=0.4, every=7, universe=None, btc_filter=True, bets=5, cap=0.35):
    def f(i, C, st):
        coins = universe or list(C)
        w = st.setdefault("w", {c: 0.0 for c in C})
        score = {c: signal(i, C, c, st) for c in coins}          # evaluated daily (stateful signals need it)
        btc = C["BTC-USDT"]; ok = (not btc_filter) or btc[i] >= sma(btc, 100, i)
        new = dict(w); rebal = (i - st["start"]) % every == 0
        if not ok: new = {c: 0.0 for c in C}
        else:
            for c in coins:
                if new[c] > 0 and score[c] == 0: new[c] = 0.0     # trend broke: leave now
            if rebal:
                raw = {c: min(cap, score[c] * (T / bets) / vol(C[c], i)) for c in coins}
                tot = sum(raw.values()); k = 1.0 / tot if tot > 1.0 else 1.0
                new = {c: (raw[c] * k if c in raw else 0.0) for c in C}
        if all(abs(new[c] - w[c]) < 1e-9 for c in C): return None
        st["w"] = new
        return new
    return f

STRATS = [
    ("Buy&hold BTC (benchmark)", hold_btc),
    ("v1 LIVE: top3 60d weekly", momentum(60, 3, 7)),
    ("v2c: v1 + daily exit + coin SMA50 + 60% cap", momentum_v2(coin_sma=50, exposure=0.6)),
    ("v3a: pro-style SMA100 trend, vol-targeted 0.40, BTC filter", vt(sig_sma(100), 0.4)),
    ("v3b: same, vol target 0.25 (more cautious)", vt(sig_sma(100), 0.25)),
    ("v3c: Turtle Donchian 55/20, vol-targeted 0.40, BTC filter", vt(sig_turtle(), 0.4)),
    ("v3d: multi-horizon trend (20/50/100/200), vol 0.40, no BTC filter", vt(sig_multi(), 0.4, btc_filter=False)),
    ("v3e: multi-horizon, BTC+ETH only, vol 0.40", vt(sig_multi(), 0.4, universe=["BTC-USDT", "ETH-USDT"], btc_filter=False)),
]

def main():
    cfg = replace(Config(), bar="1Dutc"); data = {}
    for inst in cfg.universe:
        cs = history(cfg, inst, 1500); print(inst, len(cs), flush=True)
        if len(cs) > 400: data[inst] = {c["ts"]: c for c in cs}
    ts = sorted(set.intersection(*[set(d) for d in data.values()]))
    span = f"{datetime.datetime.utcfromtimestamp(ts[0]/1000):%Y-%m-%d} to {datetime.datetime.utcfromtimestamp(ts[-1]/1000):%Y-%m-%d}"
    full, split, calmar = [], [], []
    for name, f in STRATS:
        res = run(data, f); m = metrics(*res); full.append((name, m))
        a, b = halves(*res)
        split.append(f"| {name} | {a['ret']:+.0f}% (DD {a['mdd']:.0f}%) | {b['ret']:+.0f}% (DD {b['mdd']:.0f}%) |")
        calmar.append(f"| {name} | {m['cagr']:.0f}% | {m['mdd']:.0f}% | {m['cagr'] / max(m['mdd'], 1):.2f} |")
        print(name, "done", flush=True)
    text = (f"# Pro-style trend study v3 ({len(data)} coins, {span}, 210 days warm-up)\n\n" + table(full) +
            "\n\n## First half vs second half\n\n| strategy | first half | second half |\n|---|---|---|\n" + "\n".join(split) +
            "\n\n## Yearly growth vs worst drop (higher last column = better)\n\n| strategy | CAGR | max drawdown | CAGR/DD |\n|---|---|---|---|\n" + "\n".join(calmar) + "\n")
    print(text); os.makedirs("data", exist_ok=True); open("data/daily_v3.md", "w").write(text)
    notify("📊 دراسة v3 (أسلوب المحترفين) انتهت. النتائج في data/daily_v3.md")

if __name__ == "__main__":
    main()
