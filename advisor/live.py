"""One run = fetch new CLOSED candles from OKX (public data, no keys), update paper account, notify Telegram."""
import json, os, sys, urllib.request, urllib.parse
from .config import Config
from .paper import PaperBroker
from .risk import Risk
from .strategy import signal
from .tg import token, chat_id

STATE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "state.json")
BAR_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1H": 3_600_000, "4H": 14_400_000}

def http_json(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "okx-advisor"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def candles(cfg: Config, inst=None, limit=300):
    q = urllib.parse.urlencode({"instId": inst or cfg.inst_id, "bar": cfg.bar, "limit": limit})
    rows = http_json(f"https://www.okx.com/api/v5/market/candles?{q}")["data"]
    out = [dict(ts=int(r[0]), o=float(r[1]), h=float(r[2]), l=float(r[3]), c=float(r[4]), v=float(r[5]))
           for r in rows if r[8] == "1"]            # closed candles only
    return sorted(out, key=lambda x: x["ts"])

def notify(text):
    tok, chat = token(), chat_id()
    if not (tok and chat):
        print("[no telegram]", text); return
    try:
        http_json(f"https://api.telegram.org/bot{tok}/sendMessage",
                  urllib.parse.urlencode({"chat_id": chat, "text": text}).encode())
    except Exception as e:
        print("telegram error", type(e).__name__)   # never print the token/URL

def load(cfg):
    b, r = PaperBroker(cfg), Risk(cfg)
    if os.path.exists(STATE):
        s = json.load(open(STATE))
        b.cash, b.pos, b.trades = s["cash"], s["pos"], s["trades"]
        r.__dict__.update(s["risk"]); last = s["last_ts"]
    else:
        last = 0
    return b, r, last

def save(b, r, last):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({"cash": b.cash, "pos": b.pos, "trades": b.trades[-200:], "last_ts": last,
               "risk": {k: v for k, v in r.__dict__.items() if k != "cfg"}}, open(STATE, "w"), indent=1)

def slip_for(cfg, inst):
    return cfg.slippage if inst in ("BTC-USDT", "ETH-USDT") else cfg.alt_slippage

def main():
    cfg = Config(); b, r, last = load(cfg)
    data = {}
    for inst in cfg.universe:
        try:
            cs = candles(cfg, inst)
            if len(cs) >= 220: data[inst] = {c["ts"]: i for i, c in enumerate(cs)}, cs
        except Exception as e:
            print("skip", inst, type(e).__name__)
    if not data: print("no data"); return
    all_ts = sorted(set.intersection(*[set(m) for m, _ in data.values()]))   # bars present for every coin
    first_run = last == 0
    new = [t for t in all_ts if t > last]
    if first_run: new = new[-1:]
    def px(inst, t):
        m, cs = data[inst]; return cs[m[t]]
    for t in new:
        idx = t // BAR_MS[cfg.bar]
        held = b.pos["inst"] if b.pos else None
        eq_price = px(held, t)["c"] if held in data else (b.pos["entry"] if b.pos else 0)
        eq = b.equity(eq_price)
        r.new_bar(str(t // 86_400_000), eq, idx)
        was_halted = r.halted
        if b.pos and held in data:
            res = b.check_exit(px(held, t), idx)
            if res:
                r.closed(idx)
                eq = b.equity(0)
                notify(f"{'✅' if res[1] > 0 else '❌'} PAPER: sold {held} ({res[0]}) P&L {res[1]:+.2f} USDT | equity {eq:.2f}")
        if r.halted and not was_halted:
            notify("🛑 BOT HALTED: max drawdown reached. Human review needed.")
        if b.pos is None and not r.halted:
            ok, why = r.allowed(b.equity(0), idx)
            if ok:
                best = None
                for inst, (m, cs) in data.items():
                    i = m[t]
                    sig = signal(cs[max(0, i - 299): i + 1], cfg)
                    if sig and (best is None or sig["score"] > best[1]["score"]): best = (inst, sig)
                if best:
                    inst, sig = best; sl = slip_for(cfg, inst)
                    q = r.size(b.equity(0), sig["entry"], sig["stop"], sl)
                    if q > 0 and b.buy(q, sig["entry"], sig["stop"], sig["target"], sig["why"], idx, inst, sl):
                        r.opened()
                        notify(f"🟢 PAPER: bought {q:.5f} {inst} @ {sig['entry']:.4f}\nstop {sig['stop']:.4f} | target {sig['target']:.4f}\nwhy: {sig['why']} (best of {len(data)} coins)")
    last = all_ts[-1]
    save(b, r, last)
    held = b.pos["inst"] if b.pos else None
    eq = b.equity(px(held, last)["c"]) if held in data else b.equity(0)
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":      # manual run = status check
        notify(f"ℹ️ Advisor is running (paper mode), scanning {len(data)} coins. equity {eq:.2f} USDT | open position: {held or 'no'} | trades so far: {len(b.trades)}")
    print(f"equity {eq:.2f} coins={len(data)} pos={held or 'no'} trades={len(b.trades)} halted={r.halted}")

if __name__ == "__main__":
    main()
