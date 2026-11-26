"""Study of momentum-rotation v2 variants vs the live v1 rule. Variants are FIXED in advance (no tuning),
and every variant is reported with a first-half / second-half split so an overfit one shows up."""
import os, datetime
from dataclasses import replace
from .config import Config
from .backtest import history
from .live import notify
from .daily import run, metrics, sma, momentum, hold_btc, table


def momentum_v2(look=60, top=3, every=7, filt_n=100, daily_exit=True, coin_sma=0, exposure=1.0, keep_rank=None):
    """Same idea as v1 (top coins by momentum, BTC>SMA100 filter) plus optional safety layers:
    - daily_exit: leave to cash the day BTC closes under its SMA (v1 only looked once a week)
    - coin_sma: only hold a coin while it is above its own SMA (exit it as soon as it breaks down)
    - exposure: max share of money invested (rest stays in cash)
    - keep_rank: keep a coin we already hold while it is still in the top N (fewer trades, fewer fees)"""
    keep_rank = keep_rank or top
    def f(i, C, st):
        w = st.setdefault("w", {c: 0.0 for c in C})
        btc = C["BTC-USDT"]; ok = btc[i] >= sma(btc, filt_n, i)
        new = dict(w); rebal = (i - st["start"]) % every == 0
        if not ok and (daily_exit or rebal): new = {c: 0.0 for c in C}
        else:
            if coin_sma:
                for c in C:
                    if new[c] > 0 and C[c][i] < sma(C[c], coin_sma, i): new[c] = 0.0
            if rebal and ok:
                mom = {c: C[c][i] / C[c][i - look] - 1 for c in C}
                rank = sorted(C, key=lambda c: mom[c], reverse=True)
                good = lambda c: mom[c] > 0 and (not coin_sma or C[c][i] >= sma(C[c], coin_sma, i))
                keep = [c for c in rank[:keep_rank] if new[c] > 0 and good(c)]
                pick = keep + [c for c in rank if c not in keep and good(c)][:max(0, top - len(keep))]
                new = {c: (exposure / top if c in pick else 0.0) for c in C}
        if new == w: return None
        st["w"] = new
        return new
    return f


STRATS = [
    ("Buy&hold BTC (benchmark)", hold_btc),
    ("v1 LIVE: top3 60d, weekly, BTC>SMA100", momentum(60, 3, 7)),
    ("v2a: v1 + daily BTC exit", momentum_v2()),
    ("v2b: v2a + coin above own SMA50", momentum_v2(coin_sma=50)),
    ("v2c: v2b + max 60% invested", momentum_v2(coin_sma=50, exposure=0.6)),
    ("v2d: v2b + keep coin while in top 5 (fewer fees)", momentum_v2(coin_sma=50, keep_rank=5)),
    ("v2e: v2d + max 60% invested", momentum_v2(coin_sma=50, keep_rank=5, exposure=0.6)),
]


def halves(curve, fees, trades, tim):
    mid = len(curve) // 2
    return [metrics(curve[a:b], fees, trades, tim, start_cash=curve[a][1]) for a, b in ((0, mid), (mid, len(curve)))]


def main():
    cfg = replace(Config(), bar="1Dutc"); data = {}
    for inst in cfg.universe:
        cs = history(cfg, inst, 1500); print(inst, len(cs), flush=True)
        if len(cs) > 400: data[inst] = {c["ts"]: c for c in cs}
    ts = sorted(set.intersection(*[set(d) for d in data.values()]))
    span = f"{datetime.datetime.utcfromtimestamp(ts[0]/1000):%Y-%m-%d} to {datetime.datetime.utcfromtimestamp(ts[-1]/1000):%Y-%m-%d}"
    full, split = [], []
    for name, f in STRATS:
        res = run(data, f); full.append((name, metrics(*res)))
        a, b = halves(*res)
        split.append(f"| {name} | {a['ret']:+.0f}% (DD {a['mdd']:.0f}%) | {b['ret']:+.0f}% (DD {b['mdd']:.0f}%) |")
        print(name, "done", flush=True)
    text = (f"# Momentum v2 study ({len(data)} coins, {span}, 210 days warm-up)\n\n" + table(full) +
            "\n\n## First half vs second half of the period (an overfit variant wins one half only)\n\n"
            "| strategy | first half | second half |\n|---|---|---|\n" + "\n".join(split) + "\n")
    print(text); os.makedirs("data", exist_ok=True); open("data/daily_v2.md", "w").write(text)
    notify("📊 دراسة النسخة v2 انتهت. النتائج محفوظة في data/daily_v2.md")


if __name__ == "__main__":
    main()
