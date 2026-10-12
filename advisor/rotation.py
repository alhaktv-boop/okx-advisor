"""Live PAPER momentum rotation (daily bars). Rules were fixed before testing:
 - every 7 days: if BTC close < SMA100 -> hold cash
 - else hold the top 3 coins by 60-day return (only those with positive return), 1/3 each
Runs once a day on GitHub Actions. No exchange keys. Paper money only."""
import json, os
from dataclasses import replace
from .config import Config
from .live import candles, notify
from .daily import sma, FEE, SLIP

STATE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rotation.json")
DAY = 86_400_000
LOOK, TOP, EVERY, FILT, START = 60, 3, 7, 100, 400.0
SCALE = 0.995     # keep a little cash so fees never push cash negative

def load():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {"cash": START, "units": {}, "curw": {}, "last_ts": 0, "last_rebal": 0, "equity": [], "log": [], "btc0": None}

def save(s):
    s["equity"] = s["equity"][-800:]; s["log"] = s["log"][-100:]
    os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(s, open(STATE, "w"), indent=1)

def decide(C, i):
    btc = C["BTC-USDT"]
    if btc[i] < sma(btc, FILT, i): return {c: 0.0 for c in C}, "BTC under its 100-day average: stay in cash"
    rank = sorted(C, key=lambda c: C[c][i] / C[c][i - LOOK] - 1, reverse=True)
    pick = [c for c in rank[:TOP] if C[c][i] / C[c][i - LOOK] - 1 > 0]
    return {c: (SCALE / TOP if c in pick else 0.0) for c in C}, ("top coins by 60-day momentum: " + ", ".join(f"{c.split('-')[0]} {C[c][i]/C[c][i-LOOK]*100-100:+.0f}%" for c in pick) if pick else "no coin has positive momentum: cash")

def execute(s, targets, px):
    eq = s["cash"] + sum(u * px[c] for c, u in s["units"].items() if c in px)
    acts = []
    for c, w in sorted(targets.items(), key=lambda kv: kv[1] - s["curw"].get(kv[0], 0.0)):   # sells first
        if abs(w - s["curw"].get(c, 0.0)) < 1e-9: continue
        cur = s["units"].get(c, 0.0) * px[c]; diff = w * eq - cur
        cost = abs(diff) * (FEE + SLIP); p = px[c] * (1 + SLIP if diff > 0 else 1 - SLIP)
        s["units"][c] = s["units"].get(c, 0.0) + diff / px[c]; s["cash"] -= diff + cost; s["curw"][c] = w
        acts.append(f"{'شراء' if diff > 0 else 'بيع'} {c.split('-')[0]} بقيمة {abs(diff):.0f}")
    return acts

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
        due = first or t - s["last_rebal"] >= EVERY * DAY
        if due:
            targets, why = decide(C, i)
            acts = execute(s, targets, px); s["last_rebal"] = t
            s["log"].append({"ts": t, "why": why, "acts": acts})
            if acts or first:
                notify("🔄 إعادة توازن (تجريبي): " + why + ("\n" + "\n".join(acts) if acts else "\nلا تغيير في المراكز"))
        eq = s["cash"] + sum(u * px[c] for c, u in s["units"].items() if c in px)
        s["equity"].append({"ts": t, "eq": round(eq, 2), "btc": round(px["BTC-USDT"], 2)})
        s["last_ts"] = t
    save(s)
    last = s["equity"][-1]; held = [c.split("-")[0] for c, w in s["curw"].items() if w > 0]
    bh = START * last["btc"] / s["btc0"]
    line = f"equity {last['eq']:.2f} (BTC hold would be {bh:.2f}) | holding: {', '.join(held) or 'cash'}"
    print(line)
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        notify(f"ℹ️ المستشار (دوران الزخم، تجريبي): رصيدك الوهمي {last['eq']:.2f} من 400. لو اشتريت BTC فقط لكان {bh:.2f}. المراكز الحالية: {', '.join(held) or 'نقد'}")

if __name__ == "__main__":
    main()
