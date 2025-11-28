# Options AI

Options trading tool for covered call recommendations. Connects to Schwab API to analyze real positions and suggest optimal covered call strategies.

<img width="1325" height="1181" alt="image" src="https://github.com/user-attachments/assets/14c8dcae-6e79-46ee-8c0f-cf889160c734" />

## Features

- Real-time stock charts (1D to 5Y) with TradingView-style interface
- Fetches actual portfolio positions from Schwab
- Covered call recommendations filtered by delta (0.10-0.30) and DTE (1-14 days)
- Sortable tables with weekly/annualized returns

## Setup
```bash
poetry install
cp .env.example .env  # Add your API keys
poetry run python app.py
```

Open http://localhost:5001

## Schwab API Setup

1. Go to [developer.schwab.com](https://developer.schwab.com)
2. Create an account and log in
3. Create a new app
4. Select "Accounts and Trading Production" (includes market data)
5. Set callback URL to `https://127.0.0.1`
6. Wait 1-3 days for approval
7. Copy your App Key and Secret to `.env`

On first run, you'll be prompted to authenticate via browser. The library handles token refresh automatically (tokens expire after 7 days of inactivity).

## Environment Variables

- `SCHWAB_APP_KEY` - Schwab API app key
- `SCHWAB_APP_SECRET` - Schwab API app secret
- `OPENAI_API_KEY` - OpenAI API key (for future LLM explanations)
