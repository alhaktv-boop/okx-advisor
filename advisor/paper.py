from .config import Config

class PaperBroker:
    """Simulated spot account with realistic fees and slippage."""
    def __init__(self, cfg: Config):
        self.cfg, self.cash, self.pos = cfg, cfg.start_cash, None
        self.trades = []

    def equity(self, price: float) -> float:
        return self.cash + (self.pos["qty"] * price if self.pos else 0.0)

    def buy(self, qty, price, stop, target, why, bar, inst=None, slip=None):
        slip = self.cfg.slippage if slip is None else slip
        px = price * (1 + slip)
        cost = qty * px; fee = cost * self.cfg.fee_rate
        if cost + fee > self.cash: return False
        self.cash -= cost + fee
        self.pos = dict(inst=inst, slip=slip, qty=qty, entry=px, stop=stop, target=target, why=why, bar=bar, fee_in=fee)
        return True

    def check_exit(self, candle, bar):
        """Stop is checked before target on the same candle (pessimistic)."""
        p = self.pos
        if not p: return None
        if candle["l"] <= p["stop"]: exit_px, kind = p["stop"], "stop"
        elif candle["h"] >= p["target"]: exit_px, kind = p["target"], "target"
        else: return None
        px = exit_px * (1 - p.get("slip", self.cfg.slippage))
        proceeds = p["qty"] * px; fee = proceeds * self.cfg.fee_rate
        self.cash += proceeds - fee
        pnl = proceeds - fee - p["qty"] * p["entry"] - p["fee_in"]
        self.trades.append(dict(inst=p.get("inst"), bar_in=p["bar"], bar_out=bar, kind=kind, pnl=pnl, why=p["why"]))
        self.pos = None
        return kind, pnl
