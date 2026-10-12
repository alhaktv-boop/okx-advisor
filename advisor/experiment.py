"""Walk-forward comparison of strategy variants. Pick the best on TRAIN, report it on unseen TEST."""
import sys, os, itertools
from dataclasses import replace
from .config import Config
from .backtest import history, simulate
from .live import BAR_MS, notify

def metrics(b, curve, cfg):
    tr = b.trades; n = len(tr)
    end = curve[-1][1] if curve else cfg.start_cash
    peak, mdd = cfg.start_cash, 0.0
    for _, e in curve: peak = max(peak, e); mdd = max(mdd, (peak - e) / peak)
    gw = sum(x["pnl"] for x in tr if x["pnl"] > 0); gl = -sum(x["pnl"] for x in tr if x["pnl"] <= 0)
    return dict(n=n, ret=(end / cfg.start_cash - 1) * 100, pf=(gw / gl if gl else 99.0), mdd=mdd * 100,
                win=(sum(1 for x in tr if x["pnl"] > 0) / n * 100 if n else 0), fees=sum(x["fees"] for x in tr))

def fmt(m): return f"{m['n']} trades, win {m['win']:.0f}%, return {m['ret']:+.1f}%, PF {m['pf']:.2f}, maxDD {m['mdd']:.1f}%, fees {m['fees']:.1f}"

def main():
    base = Config(); plans = {"15m": 90, "1H": 180}; out = ["# Walk-forward experiment (train = first 60%, test = last 40%)"]
    results = []
    for bar, days in plans.items():
        cfg0 = replace(base, bar=bar); data = {}
        for inst in cfg0.universe:
            cs = history(cfg0, inst, days)
            if len(cs) > 1000: data[inst] = {c["ts"]: c for c in cs}
        ts = sorted(set.intersection(*[set(m) for m in data.values()]))
        split = ts[int(len(ts) * 0.6)]
        btc = data["BTC-USDT"]; bh_test = (btc[ts[-1]]["c"] / btc[split]["c"] - 1) * 100
        print(bar, len(ts), "aligned bars", flush=True)
        for mode, (sa, ta) in itertools.product(("pullback", "breakout"), ((1.5, 3.0), (2.0, 4.0), (3.0, 6.0))):
            cfg = replace(cfg0, mode=mode, stop_atr=sa, target_atr=ta)
            b1, _, c1 = simulate(data, cfg, end_ts=split); b2, _, c2 = simulate(data, cfg, start_ts=split)
            results.append((bar, mode, sa, ta, metrics(b1, c1, cfg), metrics(b2, c2, cfg), bh_test))
            print(bar, mode, sa, ta, "train", fmt(results[-1][4]), "| test", fmt(results[-1][5]), flush=True)
    out.append("| bar | mode | stop/target ATR | TRAIN | TEST (unseen) |\n|---|---|---|---|---|")
    for bar, mode, sa, ta, tr, te, bh in results:
        out.append(f"| {bar} | {mode} | {sa}/{ta} | {fmt(tr)} | {fmt(te)} |")
    out.append("\nBTC buy&hold over test period: " + ", ".join(f"{r[0]} {r[6]:+.1f}%" for r in results[::6]))
    best = max((r for r in results if r[4]["n"] >= 10), key=lambda r: r[4]["ret"], default=None)
    if best:
        out.append(f"\nBest on TRAIN: {best[0]} {best[1]} {best[2]}/{best[3]} -> TRAIN {fmt(best[4])} -> TEST {fmt(best[5])}")
    pos = [r for r in results if r[5]["ret"] > 0 and r[4]["ret"] > 0]
    out.append(f"Variants profitable on BOTH train and test: {len(pos)} of {len(results)}")
    text = "\n".join(out); print(text)
    os.makedirs("data", exist_ok=True); open("data/experiments.md", "w").write(text + "\n")
    short = out[-3] if best else ""
    notify("🧪 Experiment finished.\n" + (f"Best on train -> test: {fmt(best[5])}\n" if best else "") + out[-1])

if __name__ == "__main__":
    main()
