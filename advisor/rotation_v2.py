"""Live PAPER momentum rotation v2c (daily bars) - runs next to v1 for a fair comparison. Paper money only.
Rules (fixed in advance, from the 4-year study in data/daily_v2.md):
 - every day: if BTC close < SMA100 -> everything to cash (v1 only checked weekly)
 - every day: sell any coin whose close is under its own SMA50
 - every 7 days: hold the top 3 coins by 60-day return (positive return, above own SMA50), max 60% of money invested."""
import os, json
from dataclasses import replace
from .config import Config
from .live import candles, notify
from .daily import sma
from . import rotation as r1

STATE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rotation_v2.json")
LOOK, TOP, EVERY, FILT, COIN_SMA, EXPOSURE, START = 60, 3, 7, 100, 50, 0.6, 400.0
DAY = r1.DAY

def load():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {"cash": START, "units": {}, "curw": {}, "last_ts": 0, "last_rebal": 0, "equity": [], "log": [], "btc0": None}

def save(s):
    s["equity"] = s["equity"][-800:]; s["log"] = s["log"][-100:]
    os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(s, open(STATE, "w"), indent=1)

def decide(C, i, curw, rebal):
    """returns (weights, reason or None). C = {coin: [closes]}"""
    btc = C["BTC-USDT"]; w = {c: curw.get(c, 0.0) for c in C}
    if btc[i] < sma(btc, FILT, i):
        return {c: 0.0 for c in C}, "BTC under its 100-day average: stay in cash"
    why = None
    for c in C:
        if w[c] > 0 and C[c][i] < sma(C[c], COIN_SMA, i): w[c] = 0.0; why = f"{c.split('-')[0]} fell under its 50-day average: sold"
    if rebal:
        mom = {c: C[c][i] / C[c][i - LOOK] - 1 for c in C}
        rank = sorted(C, key=lambda c: mom[c], reverse=True)
        good = lambda c: mom[c] > 0 and C[c][i] >= sma(C[c], COIN_SMA, i)
        keep = [c for c in rank[:TOP] if w[c] > 0 and good(c)]
        pick = keep + [c for c in rank if c not in keep and good(c)][:max(0, TOP - len(keep))]
        w = {c: (r1.SCALE * EXPOSURE / TOP if c in pick else 0.0) for c in C}
        why = ("top coins by 60-day momentum: " + ", ".join(f"{c.split('-')[0]} {mom[c]*100:+.0f}%" for c in pick)) if pick else "no coin qualifies: cash"
    return w, why

def main():
    cfg = replace(Config(), bar="1Dutc"); s = load(); data = {}
    for inst in cfg.universe:
        try:
            cs = candles(cfg, inst)
            if len(cs) >= LOOK + 10: data[inst] = {c["ts"]: c["c"] for c in cs}
        except Exception as e: print("skip", inst, type(e).__name__)
    if "BTC-USDT" not in data: print("no BTC data"); return
    ts = sorted(set.intersection(*[set(d) for d in data.values()]))
    if len(ts) < FILT + 5: print("not enough days"); return
    C = {c: [d[t] for t in ts] for c, d in data.items()}
    first = s["last_ts"] == 0
    new = [k for k, t in enumerate(ts) if t > s["last_ts"]]
    if first: new = new[-1:]
    for i in new:
        t = ts[i]; px = {c: C[c][i] for c in C}
        if s["btc0"] is None: s["btc0"] = px["BTC-USDT"]
        rebal = first or t - s["last_rebal"] >= EVERY * DAY
        w, why = decide(C, i, s["curw"], rebal)
        if rebal: s["last_rebal"] = t
        acts = r1.execute(s, w, px)
        if acts or first:
            s["log"].append({"ts": t, "why": why, "acts": acts})
            notify("🔄 النسخة v2c (تجريبي): " + (why or "") + ("\n" + "\n".join(acts) if acts else "\nلا تغيير في المراكز"))
        eq = s["cash"] + sum(u * px[c] for c, u in s["units"].items() if c in px)
        s["equity"].append({"ts": t, "eq": round(eq, 2), "btc": round(px["BTC-USDT"], 2)})
        s["last_ts"] = t
    save(s)
    last = s["equity"][-1]; held = [c.split("-")[0] for c, x in s["curw"].items() if x > 0]
    print(f"v2c equity {last['eq']:.2f} (BTC hold would be {START * last['btc'] / s['btc0']:.2f}) | holding: {', '.join(held) or 'cash'}")

if __name__ == "__main__":
    main()
