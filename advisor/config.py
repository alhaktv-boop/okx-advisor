"""All limits live here, in code. The AI can never change them."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    inst_id: str = "BTC-USDT"          # start with one liquid pair only
    bar: str = "5m"                    # candle size
    start_cash: float = 400.0          # paper money (USDT ~ EUR)
    fee_rate: float = 0.001            # 0.1% per side (OKX spot taker, worst case)
    slippage: float = 0.0005           # 0.05% assumed slippage per side
    risk_per_trade: float = 0.01       # lose max 1% of equity if stop is hit
    max_position_pct: float = 0.30     # never put >30% of equity in one trade
    max_daily_loss_pct: float = 0.03   # stop for the day at -3% equity
    max_trades_per_day: int = 6        # fees kill high frequency
    cooldown_bars: int = 6             # wait after closing a trade
    stop_atr: float = 1.5              # stop distance = 1.5 * ATR
    target_atr: float = 3.0            # take profit = 3 * ATR (reward:risk 2:1)
    min_edge_pct: float = 0.006        # target must be >= 0.6% away (covers ~0.3% costs x2)
    max_drawdown_halt_pct: float = 0.15  # hard stop of the whole bot at -15% from peak
