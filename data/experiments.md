# Walk-forward experiment (train = first 60%, test = last 40%)
| bar | mode | stop/target ATR | TRAIN | TEST (unseen) |
|---|---|---|---|---|
| 15m | pullback | 1.5/3.0 | 46 trades, win 35%, return -6.4%, PF 0.33, maxDD 6.6%, fees 10.7 | 35 trades, win 29%, return -4.7%, PF 0.42, maxDD 5.1%, fees 8.2 |
| 15m | pullback | 2.0/4.0 | 40 trades, win 30%, return -5.3%, PF 0.48, maxDD 5.4%, fees 9.2 | 29 trades, win 17%, return -6.8%, PF 0.24, maxDD 7.1%, fees 6.7 |
| 15m | pullback | 3.0/6.0 | 30 trades, win 27%, return -4.6%, PF 0.50, maxDD 4.7%, fees 6.9 | 25 trades, win 16%, return -9.4%, PF 0.14, maxDD 9.6%, fees 5.7 |
| 15m | breakout | 1.5/3.0 | 147 trades, win 33%, return -13.5%, PF 0.49, maxDD 13.9%, fees 32.3 | 107 trades, win 38%, return -8.8%, PF 0.63, maxDD 10.8%, fees 24.9 |
| 15m | breakout | 2.0/4.0 | 126 trades, win 37%, return -8.3%, PF 0.68, maxDD 9.6%, fees 28.5 | 88 trades, win 41%, return -3.9%, PF 0.83, maxDD 9.8%, fees 21.1 |
| 15m | breakout | 3.0/6.0 | 78 trades, win 38%, return -1.2%, PF 0.94, maxDD 10.1%, fees 17.8 | 49 trades, win 35%, return -3.3%, PF 0.82, maxDD 9.2%, fees 11.4 |
| 1H | pullback | 1.5/3.0 | 23 trades, win 30%, return -4.7%, PF 0.40, maxDD 5.1%, fees 5.4 | 22 trades, win 32%, return -2.3%, PF 0.69, maxDD 3.8%, fees 5.3 |
| 1H | pullback | 2.0/4.0 | 20 trades, win 30%, return -4.8%, PF 0.44, maxDD 5.3%, fees 4.7 | 19 trades, win 26%, return -4.8%, PF 0.45, maxDD 6.7%, fees 4.5 |
| 1H | pullback | 3.0/6.0 | 17 trades, win 29%, return -3.9%, PF 0.57, maxDD 4.7%, fees 3.9 | 12 trades, win 58%, return +3.1%, PF 1.69, maxDD 3.6%, fees 2.8 |
| 1H | breakout | 1.5/3.0 | 42 trades, win 43%, return +1.1%, PF 1.11, maxDD 3.9%, fees 10.2 | 65 trades, win 37%, return -5.2%, PF 0.76, maxDD 6.0%, fees 15.1 |
| 1H | breakout | 2.0/4.0 | 37 trades, win 41%, return +0.2%, PF 1.02, maxDD 3.9%, fees 8.9 | 47 trades, win 45%, return +4.7%, PF 1.28, maxDD 5.6%, fees 11.1 |
| 1H | breakout | 3.0/6.0 | 28 trades, win 39%, return -0.5%, PF 0.96, maxDD 5.5%, fees 6.7 | 28 trades, win 50%, return +6.6%, PF 1.56, maxDD 5.3%, fees 6.5 |

BTC buy&hold over test period: 15m +5.0%, 1H +29.4%

Best on TRAIN: 1H breakout 1.5/3.0 -> TRAIN 42 trades, win 43%, return +1.1%, PF 1.11, maxDD 3.9%, fees 10.2 -> TEST 65 trades, win 37%, return -5.2%, PF 0.76, maxDD 6.0%, fees 15.1
Variants profitable on BOTH train and test: 1 of 12
