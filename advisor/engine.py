"""Runs the strategy over candles. Used by both the backtest and the live paper loop."""
from .config import Config
from .strategy import signal
from .paper import PaperBroker
from .risk import Risk

def run(candles, cfg: Config = Config(), approve=None):
    """approve: optional callable(signal, candles)->bool (the AI advisor). None = rules only."""
    broker, risk, log = PaperBroker(cfg), Risk(cfg), []
    for i in range(len(candles)):
        c = candles[i]
        day = str(c["ts"] // 86_400_000)
        risk.new_bar(day, broker.equity(c["c"]), i)
        res = broker.check_exit(c, i)           # exit first, on this candle
        if res: risk.closed(i)
        if broker.pos is None and not risk.halted:
            ok, _ = risk.allowed(broker.equity(c["c"]), i)
            if ok:
                window = candles[max(0, i - 399): i + 1]
                sig = signal(window, cfg)
                if sig and (approve is None or approve(sig, window)):
                    qty = risk.size(broker.equity(c["c"]), sig["entry"], sig["stop"])
                    if qty > 0 and broker.buy(qty, sig["entry"], sig["stop"], sig["target"], sig["why"], i):
                        risk.opened()
    last = candles[-1]["c"]
    return broker, risk, broker.equity(last)

def report(broker, equity, cfg: Config):
    t = broker.trades; n = len(t); wins = sum(1 for x in t if x["pnl"] > 0)
    return {"trades": n, "win_rate": round(wins / n, 3) if n else None,
            "net_pnl": round(equity - cfg.start_cash, 2),
            "return_pct": round((equity / cfg.start_cash - 1) * 100, 2)}
