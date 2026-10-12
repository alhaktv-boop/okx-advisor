"""Daily-bar portfolio strategies vs buy&hold, on real OKX history. Parameters are FIXED in advance (no tuning)."""
import os, sys, math, datetime
from dataclasses import replace
from .config import Config
from .backtest import history
from .live import notify

FEE, SLIP = 0.001, 0.0007   # per side

def sma(xs, n, i): return sum(xs[i - n + 1:i + 1]) / n

# ---- strategies: f(i, closes{coin:[...]}, state) -> dict coin->target weight, or None (= keep) ----
def hold_btc(i, C, st):
    return {"BTC-USDT": 1.0} if i == st["start"] else None

def hold_basket(i, C, st):
    return {c: 1.0 / len(C) for c in C} if i == st["start"] else None

def donchian(n_in, n_out):
    def f(i, C, st):
        w = {}
        for c, x in C.items():
            held = st.setdefault("held", {}).get(c, False)
            if not held and x[i] > max(x[i - n_in:i]): held = True
            elif held and x[i] < min(x[i - n_out:i]): held = False
            st["held"][c] = held; w[c] = 1.0 / len(C) if held else 0.0
        return w
    return f

def sma_trend(n):
    def f(i, C, st): return {c: (1.0 / len(C) if x[i] > sma(x, n, i) else 0.0) for c, x in C.items()}
    return f

def momentum(look, top, every, filt_n=100):
    def f(i, C, st):
        if (i - st["start"]) % every: return None
        btc = C["BTC-USDT"]
        if filt_n and btc[i] < sma(btc, filt_n, i): return {c: 0.0 for c in C}      # market filter: cash
        rank = sorted(C, key=lambda c: C[c][i] / C[c][i - look] - 1, reverse=True)
        pick = [c for c in rank[:top] if C[c][i] / C[c][i - look] - 1 > 0]
        return {c: (1.0 / top if c in pick else 0.0) for c in C}
    return f

def dca_filtered(every=7, n=100, parts=26):
    def f(i, C, st):
        if (i - st["start"]) % every or st.get("done", 0) >= parts: return None
        btc = C["BTC-USDT"]; st["done"] = st.get("done", 0) + 1
        if btc[i] < sma(btc, n, i): st["done"] -= 1; return None        # skip weeks below trend
        cur = st.setdefault("dca_w", 0.0); st["dca_w"] = min(1.0, cur + 1.0 / parts)
        return {"BTC-USDT": st["dca_w"]}
    return f

# ---- engine ----
def run(data, strat, start_cash=400.0, warm=210):
    coins = list(data); days = sorted(set.intersection(*[set(d) for d in data.values()]))
    O = {c: [data[c][t]["o"] for t in days] for c in coins}; C = {c: [data[c][t]["c"] for t in days] for c in coins}
    st = {"start": warm}; cash, units, curw = start_cash, {c: 0.0 for c in coins}, {c: 0.0 for c in coins}
    curve, fees, trades, inmkt = [], 0.0, 0, 0
    pending = None
    for i in range(warm, len(days)):
        if pending:                                           # execute at today's open, signal came from yesterday's close
            eq_open = cash + sum(units[c] * O[c][i] for c in coins)
            for c, w in pending.items():
                if abs(w - curw[c]) < 1e-9: continue
                tgt = w * eq_open; cur = units[c] * O[c][i]; diff = tgt - cur
                cost = abs(diff) * (FEE + SLIP); fees += cost; trades += 1
                units[c] += diff / O[c][i]; cash -= diff + cost; curw[c] = w
            pending = None
        eq = cash + sum(units[c] * C[c][i] for c in coins)
        curve.append((days[i], eq)); inmkt += any(units[c] > 0 for c in coins)
        out = strat(i, C, st)
        if out is not None: pending = out
    return curve, fees, trades, inmkt / max(1, len(curve))

def metrics(curve, fees, trades, tim, start_cash=400.0):
    eq = [e for _, e in curve]; rets = [eq[k] / eq[k - 1] - 1 for k in range(1, len(eq))]
    mu = sum(rets) / len(rets); sd = math.sqrt(sum((r - mu) ** 2 for r in rets) / len(rets)) or 1e-9
    peak, mdd = eq[0], 0.0
    for e in eq: peak = max(peak, e); mdd = max(mdd, (peak - e) / peak)
    yrs = len(eq) / 365
    by_year = {}
    for (t, e), (t0, e0) in zip(curve[1:], curve[:-1]):
        y = datetime.datetime.utcfromtimestamp(t / 1000).year; by_year.setdefault(y, [e0, e])[1] = e
    return dict(ret=(eq[-1] / start_cash - 1) * 100, cagr=((eq[-1] / start_cash) ** (1 / yrs) - 1) * 100 if yrs > 0.1 else 0,
                mdd=mdd * 100, sharpe=mu / sd * math.sqrt(365), fees=fees, trades=trades, tim=tim * 100,
                years={y: (v[1] / v[0] - 1) * 100 for y, v in by_year.items()})

def table(results):
    rows = ["| strategy | total | per year | max drawdown | Sharpe | trades | fees | time in market |", "|---|---|---|---|---|---|---|---|"]
    for name, m in results:
        yrs = ", ".join(f"{y}: {v:+.0f}%" for y, v in sorted(m["years"].items()))
        rows.append(f"| {name} | {m['ret']:+.0f}% | {yrs} | {m['mdd']:.0f}% | {m['sharpe']:.2f} | {m['trades']} | {m['fees']:.1f} | {m['tim']:.0f}% |")
    return "\n".join(rows)

STRATS = [
    ("Buy&hold BTC (benchmark)", hold_btc),
    ("Buy&hold 10 coins equal (benchmark)", hold_basket),
    ("Donchian 50/20 (trend, 10 coins)", donchian(50, 20)),
    ("Donchian 20/10", donchian(20, 10)),
    ("Donchian 100/50", donchian(100, 50)),
    ("Price > SMA100 (trend, 10 coins)", sma_trend(100)),
    ("Price > SMA50", sma_trend(50)),
    ("Price > SMA200", sma_trend(200)),
    ("Momentum rotation: top3 by 30d, weekly, BTC>SMA100 filter", momentum(30, 3, 7)),
    ("Momentum rotation: top3 by 60d, weekly, filter", momentum(60, 3, 7)),
    ("Momentum rotation: top3 by 30d, weekly, NO filter", momentum(30, 3, 7, 0)),
    ("DCA BTC weekly 26 parts, only above SMA100", dca_filtered()),
]

def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    cfg = replace(Config(), bar="1Dutc"); data = {}
    for inst in cfg.universe:
        cs = history(cfg, inst, days); print(inst, len(cs), flush=True)
        if len(cs) > 400: data[inst] = {c["ts"]: c for c in cs}
    ts = sorted(set.intersection(*[set(d) for d in data.values()]))
    span = f"{datetime.datetime.utcfromtimestamp(ts[0]/1000):%Y-%m-%d} to {datetime.datetime.utcfromtimestamp(ts[-1]/1000):%Y-%m-%d}"
    results = []
    for name, f in STRATS:
        res = run(data, f); results.append((name, metrics(*res))); print(name, "done", flush=True)
    text = f"# Daily strategies vs buy&hold ({len(data)} coins, {span}, first 210 days used as warm-up)\n\n" + table(results)
    print(text); os.makedirs("data", exist_ok=True); open("data/daily.md", "w").write(text + "\n")
    notify("📈 Daily-strategy study finished. Results are saved in data/daily.md in the repo.")

if __name__ == "__main__":
    main()
