"""Backtest the multi-coin strategy on real OKX history. Usage: python -m advisor.backtest [days]"""
import sys, time, os, json, urllib.parse
from .config import Config
from .paper import PaperBroker
from .risk import Risk
from .strategy import signal
from .live import http_json, BAR_MS, slip_for, notify

def history(cfg, inst, days):
    """Page backwards through OKX history-candles (100 per request), closed candles only."""
    need, out, after = days * 86_400_000 // BAR_MS[cfg.bar], {}, ""
    stop_ts = int(time.time() * 1000) - days * 86_400_000
    while True:
        q = {"instId": inst, "bar": cfg.bar, "limit": 100}
        if after: q["after"] = after
        for attempt in range(4):
            try:
                rows = http_json("https://www.okx.com/api/v5/market/history-candles?" + urllib.parse.urlencode(q))["data"]; break
            except Exception:
                time.sleep(1.5 * (attempt + 1)); rows = None
        if not rows: break
        for r in rows:
            if r[8] == "1": out[int(r[0])] = dict(ts=int(r[0]), o=float(r[1]), h=float(r[2]), l=float(r[3]), c=float(r[4]), v=float(r[5]))
        after = rows[-1][0]
        if int(after) <= stop_ts: break
        time.sleep(0.12)
    return sorted((c for c in out.values() if c["ts"] >= stop_ts - 300 * BAR_MS[cfg.bar]), key=lambda c: c["ts"])

def simulate(data, cfg, warmup=300, start_ts=0, end_ts=1 << 62):
    """data: {inst: {ts: candle}}; same decision logic as live.main()."""
    ts_all = sorted(set.intersection(*[set(m) for m in data.values()]))
    seq = {inst: [m[t] for t in ts_all] for inst, m in data.items()}
    b, r, curve = PaperBroker(cfg), Risk(cfg), []
    for k in range(warmup, len(ts_all)):
        t = ts_all[k]
        if t < start_ts: continue
        if t >= end_ts: break
        idx = t // BAR_MS[cfg.bar]
        held = b.pos["inst"] if b.pos else None
        r.new_bar(str(t // 86_400_000), b.equity(seq[held][k]["c"]) if held else b.cash, idx)
        if held:
            res = b.check_exit(seq[held][k], idx)
            if res: r.closed(idx)
        if b.pos is None and not r.halted and r.allowed(b.cash, idx)[0]:
            best = None
            for inst in seq:
                sig = signal(seq[inst][max(0, k - 299): k + 1], cfg)
                if sig and (best is None or sig["score"] > best[1]["score"]): best = (inst, sig)
            if best:
                inst, sig = best; sl = slip_for(cfg, inst)
                q = r.size(b.cash, sig["entry"], sig["stop"], sl)
                if q > 0 and b.buy(q, sig["entry"], sig["stop"], sig["target"], sig["why"], idx, inst, sl): r.opened()
        held = b.pos["inst"] if b.pos else None
        curve.append((t, b.equity(seq[held][k]["c"]) if held else b.cash))
    return b, r, curve

def stats(trades, curve, cfg, label):
    n = len(trades); w = [x for x in trades if x["pnl"] > 0]
    peak, mdd = cfg.start_cash, 0.0
    for _, e in curve:
        peak = max(peak, e); mdd = max(mdd, (peak - e) / peak)
    gross_w, gross_l = sum(x["pnl"] for x in w), -sum(x["pnl"] for x in trades if x["pnl"] <= 0)
    end = curve[-1][1] if curve else cfg.start_cash
    return (f"**{label}**: {n} trades | win rate {len(w)/n*100:.0f}% | net {end-cfg.start_cash:+.2f} USDT ({(end/cfg.start_cash-1)*100:+.1f}%) | "
            f"fees {sum(x['fees'] for x in trades):.2f} | profit factor {gross_w/gross_l if gross_l else float('inf'):.2f} | max drawdown {mdd*100:.1f}%") if n else f"**{label}**: no trades"

def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 45
    cfg = Config(); data = {}
    for inst in cfg.universe:
        cs = history(cfg, inst, days)
        print(inst, len(cs), "candles", flush=True)
        if len(cs) > 500: data[inst] = {c["ts"]: c for c in cs}
    b, r, curve = simulate(data, cfg)
    tr = b.trades; mid = len(tr) // 2
    first_ts = curve[0][0]; mid_ts = curve[len(curve) // 2][0]
    h1 = [x for x in tr if x["bar_in"] * BAR_MS[cfg.bar] < mid_ts]; h2 = [x for x in tr if x["bar_in"] * BAR_MS[cfg.bar] >= mid_ts]
    per = {}
    for x in tr: per.setdefault(x["inst"], []).append(x["pnl"])
    btc = data.get("BTC-USDT"); bh = ""
    if btc:
        ts = sorted(btc); bh = f"BTC buy&hold over same period: {(btc[ts[-1]]['c']/btc[ts[300]]['c']-1)*100:+.1f}%"
    lines = [f"# Backtest {days} days, {len(data)} coins, {cfg.bar} candles, start {cfg.start_cash:.0f} USDT",
             stats(tr, curve, cfg, "ALL"), stats(h1, curve, cfg, "first half (trades)") if h1 else "", stats(h2, curve, cfg, "second half (trades)") if h2 else "",
             "Per coin (trades / net pnl): " + ", ".join(f"{k} {len(v)}/{sum(v):+.2f}" for k, v in sorted(per.items())),
             bh, f"halted: {r.halted}"]
    text = "\n".join(l for l in lines if l)
    print(text)
    os.makedirs("data", exist_ok=True); open("data/backtest.md", "w").write(text + "\n")
    notify("📊 " + text.replace("**", "")[:3500])

if __name__ == "__main__":
    main()
