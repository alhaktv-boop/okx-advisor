import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from advisor.config import Config
from advisor.engine import run, report
from advisor.risk import Risk

def synth(n=6000, seed=1, drift=0.0):
    random.seed(seed); p, out = 60000.0, []
    for i in range(n):
        o = p; p *= 1 + random.gauss(drift, 0.0015)
        h = max(o, p) * (1 + abs(random.gauss(0, 0.0007))); l = min(o, p) * (1 - abs(random.gauss(0, 0.0007)))
        out.append(dict(ts=i * 300_000, o=o, h=h, l=l, c=p, v=1.0))
    return out

def test_risk_size_caps_loss():
    cfg = Config(); r = Risk(cfg)
    q = r.size(400, 60000, 59500)
    assert q * 60000 <= 400 * cfg.max_position_pct + 1e-6
    assert q * (500 + 60000 * 2 * (cfg.fee_rate + cfg.slippage)) <= 400 * cfg.risk_per_trade + 1e-6

def test_never_loses_more_than_halt():
    for seed in range(5):
        b, risk, eq = run(synth(seed=seed, drift=-0.0003))
        assert eq > 400 * (1 - 0.30), (seed, eq)

def test_trade_limit_per_day():
    b, risk, eq = run(synth(seed=3, drift=0.0002))
    from collections import Counter
    per_day = Counter(t["bar_in"] * 300_000 // 86_400_000 for t in b.trades)
    assert all(v <= Config().max_trades_per_day for v in per_day.values())

if __name__ == "__main__":
    test_risk_size_caps_loss(); test_never_loses_more_than_halt(); test_trade_limit_per_day()
    for s, d in [(1, 0), (2, 0.0002), (3, -0.0002)]:
        b, r, eq = run(synth(seed=s, drift=d)); print("seed", s, "drift", d, report(b, eq, Config()), "halted", r.halted)
    print("OK")
