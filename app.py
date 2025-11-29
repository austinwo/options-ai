import os
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request
import schwabdev
from openai import OpenAI
import anthropic

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

app = Flask(__name__, static_folder="static", static_url_path="/static")

client = schwabdev.Client(os.getenv("SCHWAB_APP_KEY"), os.getenv("SCHWAB_APP_SECRET"))


@app.route("/")
def index():
    return render_template("chart.html")


@app.route("/api/candles/<symbol>")
def get_candles(symbol):
    period = request.args.get("period", "5d")
    logger.info(f"Fetching candles for {symbol}, period={period}")

    period_map = {
        "1d": {
            "periodType": "day",
            "period": 1,
            "frequencyType": "minute",
            "frequency": 5,
        },
        "5d": {
            "periodType": "day",
            "period": 5,
            "frequencyType": "minute",
            "frequency": 5,
        },
        "1m": {
            "periodType": "month",
            "period": 1,
            "frequencyType": "daily",
            "frequency": 1,
        },
        "6m": {
            "periodType": "month",
            "period": 6,
            "frequencyType": "daily",
            "frequency": 1,
        },
        "1y": {
            "periodType": "year",
            "period": 1,
            "frequencyType": "daily",
            "frequency": 1,
        },
        "5y": {
            "periodType": "year",
            "period": 5,
            "frequencyType": "weekly",
            "frequency": 1,
        },
    }

    params = period_map.get(period, period_map["5d"])

    try:
        response = client.price_history(
            symbol,
            periodType=params["periodType"],
            period=params["period"],
            frequencyType=params["frequencyType"],
            frequency=params["frequency"],
        )
        data = response.json()
    except Exception as e:
        logger.error(f"Error fetching candles for {symbol}: {e}")
        return jsonify({"error": f"Failed to fetch price data: {str(e)}"}), 500

    candles = [
        {
            "time": c["datetime"] // 1000,
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
        }
        for c in data.get("candles", [])
    ]

    logger.info(f"Returning {len(candles)} candles for {symbol}")
    return jsonify(candles)


@app.route("/api/recommendations")
def get_recommendations():
    logger.info("Fetching recommendations for all positions")

    try:
        accounts = client.account_linked().json()
        account_hash = accounts[0]["hashValue"]
        account_data = client.account_details(account_hash, fields="positions").json()
        positions = account_data["securitiesAccount"]["positions"]
    except Exception as e:
        logger.error(f"Error fetching account positions: {e}")
        return jsonify({"error": f"Failed to fetch positions: {str(e)}"}), 500

    holdings = {}
    for pos in positions:
        if pos["instrument"]["assetType"] == "EQUITY":
            symbol = pos["instrument"]["symbol"]
            quantity = int(pos["longQuantity"])
            if quantity >= 100:
                holdings[symbol] = {
                    "shares": (quantity // 100) * 100,
                    "avgPrice": pos["averagePrice"],
                    "marketValue": pos["marketValue"],
                    "gainLoss": pos["longOpenProfitLoss"],
                }

    logger.info(f"Found {len(holdings)} positions with 100+ shares")

    recommendations = {}
    for ticker, info in holdings.items():
        contracts = info["shares"] // 100

        try:
            response = client.option_chains(ticker)
            data = response.json()
        except Exception as e:
            logger.error(f"Error fetching options chain for {ticker}: {e}")
            continue

        underlying_price = data.get("underlyingPrice", 0)
        if underlying_price <= 0:
            logger.warning(f"Invalid underlying price for {ticker}: {underlying_price}")
            continue

        candidates = []
        for exp_date, strikes in data.get("callExpDateMap", {}).items():
            for strike_price, options in strikes.items():
                opt = options[0]
                delta = abs(opt.get("delta", 0))
                dte = opt.get("daysToExpiration", 0)
                bid = opt.get("bid", 0)
                strike = opt.get("strikePrice", 0)

                if 0.09 <= delta <= 0.2 and 1 <= dte <= 14 and bid > 0:
                    weekly_return = (bid / underlying_price) * (7 / dte) * 100
                    annualized_return = (bid / underlying_price) * (365 / dte) * 100
                    total_premium = bid * contracts * 100
                    otm_dollar = strike - underlying_price
                    otm_pct = (otm_dollar / underlying_price) * 100
                    candidates.append(
                        {
                            "strike": strike,
                            "exp": exp_date.split(":")[0],
                            "dte": dte,
                            "delta": round(delta, 3),
                            "bid": bid,
                            "weeklyPct": round(weekly_return, 2),
                            "annualizedPct": round(annualized_return, 2),
                            "totalPremium": round(total_premium, 0),
                            "otmDollar": round(otm_dollar, 2),
                            "otmPct": round(otm_pct, 2),
                        }
                    )

        recommendations[ticker] = {
            "info": info,
            "price": underlying_price,
            "contracts": contracts,
            "candidates": sorted(
                candidates, key=lambda x: x["weeklyPct"], reverse=True
            )[:10],
        }

    logger.info(f"Returning recommendations for {len(recommendations)} tickers")
    return jsonify(recommendations)


@app.route("/api/recommendation/<symbol>")
def get_recommendation(symbol):
    logger.info(f"Fetching AI recommendation for {symbol}")

    try:
        accounts = client.account_linked().json()
        account_hash = accounts[0]["hashValue"]
        account_data = client.account_details(account_hash, fields="positions").json()
        positions = account_data["securitiesAccount"]["positions"]
    except Exception as e:
        logger.error(f"Error fetching account positions: {e}")
        return jsonify({"error": f"Failed to fetch positions: {str(e)}"}), 500

    position = None
    for pos in positions:
        if (
            pos["instrument"]["assetType"] == "EQUITY"
            and pos["instrument"]["symbol"] == symbol
        ):
            position = {
                "shares": int(pos["longQuantity"]),
                "avgPrice": pos["averagePrice"],
                "gainLoss": pos["longOpenProfitLoss"],
            }
            break

    if not position:
        logger.warning(f"Position not found for {symbol}")
        return jsonify({"error": "Position not found"}), 404

    try:
        response = client.option_chains(symbol)
        data = response.json()
    except Exception as e:
        logger.error(f"Error fetching options chain for {symbol}: {e}")
        return jsonify({"error": f"Failed to fetch options chain: {str(e)}"}), 500

    underlying_price = data.get("underlyingPrice", 0)
    if underlying_price <= 0:
        logger.warning(f"Invalid underlying price for {symbol}: {underlying_price}")
        return jsonify({"error": "Invalid underlying price"}), 500

    candidates = []
    for exp_date, strikes in data.get("callExpDateMap", {}).items():
        for strike_price, options in strikes.items():
            opt = options[0]
            delta = abs(opt.get("delta", 0))
            dte = opt.get("daysToExpiration", 0)
            bid = opt.get("bid", 0)
            strike = opt.get("strikePrice", 0)

            if 0.10 <= delta <= 0.30 and 1 <= dte <= 14 and bid > 0:
                contracts = position["shares"] // 100
                weekly_return = (bid / underlying_price) * (7 / dte) * 100
                annualized_return = (bid / underlying_price) * (365 / dte) * 100
                otm_dollar = strike - underlying_price
                otm_pct = (otm_dollar / underlying_price) * 100

                candidates.append(
                    {
                        "strike": strike,
                        "exp": exp_date.split(":")[0],
                        "dte": dte,
                        "delta": round(delta, 3),
                        "bid": bid,
                        "weeklyPct": round(weekly_return, 2),
                        "annualizedPct": round(annualized_return, 2),
                        "totalPremium": round(bid * contracts * 100, 0),
                        "otmDollar": round(otm_dollar, 2),
                        "otmPct": round(otm_pct, 2),
                    }
                )

    candidates = sorted(candidates, key=lambda x: x["weeklyPct"], reverse=True)[:10]

    prompt = f"""You are an options trading advisor. Give a specific covered call recommendation for {symbol}.

POSITION:
- Shares: {position["shares"]}
- Cost basis: ${position["avgPrice"]:.2f}
- Current price: ${underlying_price:.2f}
- Unrealized P/L: ${position["gainLoss"]:.0f}
- Contracts available: {position["shares"] // 100}

TOP CC CANDIDATES:
"""

    for c in candidates:
        prompt += f"- ${c['strike']} strike, {c['exp']} expiry, {c['dte']}d DTE, delta {c['delta']}, ${c['bid']:.2f} bid, {c['weeklyPct']}%/wk, {c['otmPct']:.1f}% OTM\n"

    prompt += """
INSTRUCTIONS:
1. Recommend ONE specific strike and expiry to sell (or recommend to HOLD if conditions are unfavorable)
2. Explain why this strike over others
3. Mention the key tradeoff (premium vs cushion)
4. Note any risks
5. Keep response concise — under 150 words

Format your response as:
**Recommendation: [SELL/HOLD]** [strike and expiry if selling]

[Your reasoning]
"""

    provider = request.args.get("provider", "anthropic")
    model = request.args.get("model", "")

    logger.info(f"Calling LLM provider={provider}, model={model}")

    try:
        if provider == "openai":
            if model == "o3-mini":
                response = openai_client.chat.completions.create(
                    model="o3-mini",
                    reasoning_effort="low",
                    messages=[{"role": "user", "content": prompt}],
                )
            else:
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                )
            recommendation = response.choices[0].message.content
        else:
            response = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            recommendation = response.content[0].text
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        return jsonify({"error": f"Failed to get AI recommendation: {str(e)}"}), 500

    logger.info(f"Successfully generated recommendation for {symbol}")

    return jsonify(
        {
            "symbol": symbol,
            "recommendation": recommendation,
            "candidates": candidates,
            "position": position,
            "currentPrice": underlying_price,
        }
    )


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.getenv("PORT", 5001))
    logger.info(f"Starting Options AI on port {port}, debug={debug}")
    app.run(debug=debug, port=port)
