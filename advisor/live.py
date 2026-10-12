"""One run = fetch new CLOSED candles from OKX (public data, no keys), update paper account, notify Telegram."""
import json, os, sys, urllib.request, urllib.parse
from .config import Config
from .paper import PaperBroker
from .risk import Risk
from .strategy import signal
from .tg import token, chat_id

STATE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "state.json")
BAR_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000}

def http_json(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "okx-advisor"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def candles(cfg: Config, limit=300):
    q = urllib.parse.urlencode({"instId": cfg.inst_id, "bar": cfg.bar, "limit": limit})
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

def main():
    cfg = Config(); b, r, last = load(cfg)
    cs = candles(cfg)
    if len(cs) < 220: print("not enough candles"); return
    first_run = last == 0
    new = [i for i, c in enumerate(cs) if c["ts"] > last]
    if first_run: new = new[-1:]                      # don't replay history on first run
    for i in new:
        c, idx = cs[i], cs[i]["ts"] // BAR_MS[cfg.bar]
        r.new_bar(str(c["ts"] // 86_400_000), b.equity(c["c"]), idx)
        was_halted = r.halted
        res = b.check_exit(c, idx)
        if res:
            r.closed(idx)
            notify(f"{'✅' if res[1] > 0 else '❌'} PAPER: sold {cfg.inst_id} ({res[0]}) P&L {res[1]:+.2f} USDT | equity {b.equity(c['c']):.2f}")
        if r.halted and not was_halted:
            notify("🛑 BOT HALTED: max drawdown reached. Human review needed.")
        if b.pos is None and not r.halted:
            ok, why = r.allowed(b.equity(c["c"]), idx)
            if ok:
                sig = signal(cs[max(0, i - 299): i + 1], cfg)
                if sig:
                    q = r.size(b.equity(c["c"]), sig["entry"], sig["stop"])
                    if q > 0 and b.buy(q, sig["entry"], sig["stop"], sig["target"], sig["why"], idx):
                        r.opened()
                        notify(f"🟢 PAPER: bought {q:.5f} {cfg.inst_id} @ {sig['entry']:.2f}\nstop {sig['stop']:.2f} | target {sig['target']:.2f}\nwhy: {sig['why']}")
    last = cs[-1]["ts"]
    save(b, r, last)
    print(f"equity {b.equity(cs[-1]['c']):.2f} pos={'yes' if b.pos else 'no'} trades={len(b.trades)} halted={r.halted}")

if __name__ == "__main__":
    main()
