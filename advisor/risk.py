from .config import Config

class Risk:
    def __init__(self, cfg: Config):
        self.cfg = cfg; self.day = None; self.day_start_equity = None
        self.trades_today = 0; self.peak = cfg.start_cash; self.halted = False
        self.cooldown_until = -1

    def new_bar(self, day: str, equity: float, bar_index: int):
        if day != self.day:
            self.day, self.day_start_equity, self.trades_today = day, equity, 0
        self.peak = max(self.peak, equity)
        if equity < self.peak * (1 - self.cfg.max_drawdown_halt_pct):
            self.halted = True            # permanent until a human resets it

    def allowed(self, equity: float, bar_index: int):
        c = self.cfg
        if self.halted: return False, "bot halted: max drawdown reached"
        if bar_index < self.cooldown_until: return False, "cooldown"
        if self.trades_today >= c.max_trades_per_day: return False, "daily trade limit"
        if equity < self.day_start_equity * (1 - c.max_daily_loss_pct): return False, "daily loss limit"
        return True, ""

    def size(self, equity: float, entry: float, stop: float) -> float:
        """Quantity so that hitting the stop loses at most risk_per_trade of equity."""
        c = self.cfg
        per_unit_loss = (entry - stop) + entry * 2 * (c.fee_rate + c.slippage)
        if per_unit_loss <= 0: return 0.0
        qty = equity * c.risk_per_trade / per_unit_loss
        return min(qty, equity * c.max_position_pct / entry)

    def opened(self): self.trades_today += 1
    def closed(self, bar_index: int): self.cooldown_until = bar_index + self.cfg.cooldown_bars
