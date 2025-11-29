# Options AI

Personal trading tool for covered call recommendations. Connects to Schwab API to analyze real positions and suggest optimal CC strategies with AI-powered explanations.

<img width="1186" height="1189" alt="image" src="https://github.com/user-attachments/assets/414638b2-cd41-4d1f-b877-6109b763f0ba" />


## Features

- Real-time stock charts (1D to 5Y) with TradingView-style interface
- Fetches actual portfolio positions from Schwab
- Covered call recommendations filtered by delta (0.10-0.30) and DTE (1-14 days)
- Sortable tables with weekly/annualized returns, OTM cushion
- AI-powered recommendations with reasoning (supports Claude Sonnet, GPT-4o-mini, o3-mini)

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

## AI Models

The recommendation engine supports multiple AI providers:

| Provider | Model | Usage | 
|----------|-------|-------|
| Anthropic | Claude Sonnet 4 | `?provider=anthropic` |
| OpenAI | GPT-4o-mini | `?provider=openai` |
| OpenAI | o3-mini | `?provider=openai&model=o3-mini` |

Example: `/api/recommendation/META?provider=openai&model=o3-mini`

### Model Tradeoffs

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| **Claude Sonnet 4** (default) | Fast | $$ | Balanced reasoning and speed. Best for clear, well-structured explanations. Default choice. |
| **GPT-4o-mini** | Fastest | $ | Quick responses when cost matters. Slightly less nuanced reasoning. |
| **o3-mini** | Slow | $$$ | Complex reasoning tasks. Overkill for simple recommendations but fun to compare. |

**Why Sonnet is the default:** Best balance of quality, speed, and cost for financial analysis. Produces clear, actionable recommendations without overthinking.

## Environment Variables
```
SCHWAB_APP_KEY=your_schwab_app_key
SCHWAB_APP_SECRET=your_schwab_app_secret
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
```

## Running Tests
```bash
poetry run pytest
```

## Project Structure
```
options-ai/
├── app.py              # Flask backend + API routes
├── templates/
│   └── chart.html      # Main UI template
├── static/
│   ├── app.js          # Frontend JavaScript
│   └── styles.css      # Styles
├── tests/
│   └── test_app.py     # Unit tests
├── .env.example
├── pyproject.toml
└── README.md
```
