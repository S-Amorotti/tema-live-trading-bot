# TEMA Multi-Timeframe Trend-Following Bot (Alpaca Paper Trading)

A modular, production-style live trading runner implementing a
TEMA-based multi-timeframe trend-following strategy (1H + 4H), including:

- volatility-targeted position sizing  
- ATR-based risk management  
- momentum-weighted scaling (CMO-based)  
- 1H/4H trend confirmation  
- bracket TP/SL orders  
- state persistence & logging  

This repository is designed for **paper trading only** and provides a clean template
for live algorithmic execution using the Alpaca API.


## 🚀 Quickstart

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install Packages:

```
pip install -r requirements.txt
```

3. Copy the environment example:

```
cp .env.example .env
```

4. Set your Alpaca keys inside .env:

```
APCA_API_KEY_ID=your_api _key

APCA_API_SECRET_KEY=you_api_passkey
```

5. Adjust parameters in config.py

- symbol selection
- risk knobs
- thresholds
- ATR multipliers
- crypto/equity mode

6. Run:

```
python main.py
```

## 🔒 Privacy & Security

This project uses local environment variables and does not store or transmit API keys,
credentials, or trading data to any external server except the broker (Alpaca).

To protect your privacy and security:

- Never commit your real .env file or API keys
- Ensure logs/ and state/ directories remain in .gitignore
- Delete any generated logs before publishing your project
- Use this bot with Paper Trading unless you fully understand real-market risks
- Rotate API keys immediately if they are ever exposed

By default, the bot stores only:

- timestamp of the last processed bar
- your day-start equity
- order execution logs

These remain strictly local unless you choose to share or upload them.


## ⚠️ Disclaimer

This software is provided for educational and research purposes only.
It does not constitute financial, trading, or investment advice.
The authors assume no responsibility for any losses, damages, or issues arising
from the use of this code.

Use entirely at your own risk.
