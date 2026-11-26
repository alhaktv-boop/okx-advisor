# Momentum v2 study (10 coins, 2022-12-21 to 2026-11-25, 210 days warm-up)

| strategy | total | per year | max drawdown | Sharpe | trades | fees | time in market |
|---|---|---|---|---|---|---|---|
| Buy&hold BTC (benchmark) | +102% | 2023: +41%, 2024: +121%, 2025: -6%, 2026: -31% | 53% | 0.68 | 1 | 0.7 | 100% |
| v1 LIVE: top3 60d, weekly, BTC>SMA100 | +370% | 2023: +132%, 2024: +106%, 2025: +23%, 2026: -20% | 48% | 1.08 | 160 | 155.0 | 73% |
| v2a: v1 + daily BTC exit | +362% | 2023: +126%, 2024: +109%, 2025: +10%, 2026: -11% | 45% | 1.08 | 162 | 149.0 | 61% |
| v2b: v2a + coin above own SMA50 | +326% | 2023: +154%, 2024: +76%, 2025: -7%, 2026: +2% | 43% | 1.07 | 196 | 158.2 | 86% |
| v2c: v2b + max 60% invested | +184% | 2023: +95%, 2024: +45%, 2025: -2%, 2026: +2% | 31% | 1.05 | 196 | 64.9 | 68% |
| v2d: v2b + keep coin while in top 5 (fewer fees) | +103% | 2023: +119%, 2024: -5%, 2025: -0%, 2026: -2% | 46% | 0.67 | 164 | 73.8 | 61% |
| v2e: v2d + max 60% invested | +78% | 2023: +77%, 2024: -0%, 2025: +1%, 2026: -1% | 33% | 0.69 | 164 | 37.8 | 59% |

## First half vs second half of the period (an overfit variant wins one half only)

| strategy | first half | second half |
|---|---|---|
| Buy&hold BTC (benchmark) | +180% (DD 26%) | -30% (DD 53%) |
| v1 LIVE: top3 60d, weekly, BTC>SMA100 | +451% (DD 48%) | -15% (DD 43%) |
| v2a: v1 + daily BTC exit | +423% (DD 45%) | -12% (DD 40%) |
| v2b: v2a + coin above own SMA50 | +339% (DD 43%) | -3% (DD 32%) |
| v2c: v2b + max 60% invested | +183% (DD 31%) | +0% (DD 21%) |
| v2d: v2b + keep coin while in top 5 (fewer fees) | +99% (DD 46%) | +2% (DD 31%) |
| v2e: v2d + max 60% invested | +72% (DD 33%) | +3% (DD 20%) |
