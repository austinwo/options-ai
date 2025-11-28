import os
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request
import schwabdev

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')

client = schwabdev.Client(
    os.getenv("SCHWAB_APP_KEY"),
    os.getenv("SCHWAB_APP_SECRET")
)

@app.route("/")
def index():
    return render_template("chart.html")

@app.route("/api/candles/<symbol>")
def get_candles(symbol):
    period = request.args.get("period", "5d")
    
    # Map period to Schwab API params
    period_map = {
        "1d":  {"periodType": "day",   "period": 1,  "frequencyType": "minute", "frequency": 5},
        "5d":  {"periodType": "day",   "period": 5,  "frequencyType": "minute", "frequency": 5},
        "1m":  {"periodType": "month", "period": 1,  "frequencyType": "daily",  "frequency": 1},
        "6m":  {"periodType": "month", "period": 6,  "frequencyType": "daily",  "frequency": 1},
        "1y":  {"periodType": "year",  "period": 1,  "frequencyType": "daily",  "frequency": 1},
        "5y":  {"periodType": "year",  "period": 5,  "frequencyType": "weekly", "frequency": 1},
    }
    
    params = period_map.get(period, period_map["5d"])
    
    response = client.price_history(
        symbol,
        periodType=params["periodType"],
        period=params["period"],
        frequencyType=params["frequencyType"],
        frequency=params["frequency"]
    )
    data = response.json()
    
    candles = [
        {
            "time": c["datetime"] // 1000,
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"]
        }
        for c in data.get("candles", [])
    ]
    
    return jsonify(candles)

@app.route("/api/recommendations")
def get_recommendations():
    # Get accounts and positions
    accounts = client.account_linked().json()
    account_hash = accounts[0]["hashValue"]
    account_data = client.account_details(account_hash, fields="positions").json()
    positions = account_data["securitiesAccount"]["positions"]
    
    # Extract stock holdings (100+ shares only)
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
                    "gainLoss": pos["longOpenProfitLoss"]
                }
    
    # Get CC recommendations for each holding
    recommendations = {}
    for ticker, info in holdings.items():
        contracts = info["shares"] // 100
        
        response = client.option_chains(ticker)
        data = response.json()
        underlying_price = data.get("underlyingPrice", 0)
        
        candidates = []
        for exp_date, strikes in data.get("callExpDateMap", {}).items():
            for strike_price, options in strikes.items():
                opt = options[0]
                delta = abs(opt.get("delta", 0))
                dte = opt.get("daysToExpiration", 0)
                bid = opt.get("bid", 0)
                strike = opt.get("strikePrice", 0)
                
                if 0.10 <= delta <= 0.30 and 1 <= dte <= 14 and bid > 0:
                    weekly_return = (bid / underlying_price) * (7 / dte) * 100
                    annualized_return = (bid / underlying_price) * (365 / dte) * 100
                    total_premium = bid * contracts * 100
                    otm_dollar = strike - underlying_price
                    otm_pct = (otm_dollar / underlying_price) * 100
                    candidates.append({
                        "strike": strike,
                        "exp": exp_date.split(":")[0],
                        "dte": dte,
                        "delta": round(delta, 3),
                        "bid": bid,
                        "weeklyPct": round(weekly_return, 2),
                        "annualizedPct": round(annualized_return, 2),
                        "totalPremium": round(total_premium, 0),
                        "otmDollar": round(otm_dollar, 2),
                        "otmPct": round(otm_pct, 2)
                    })
        
        recommendations[ticker] = {
            "info": info,
            "price": underlying_price,
            "contracts": contracts,
            "candidates": sorted(candidates, key=lambda x: x["weeklyPct"], reverse=True)[:5]
        }
    
    return jsonify(recommendations)

if __name__ == "__main__":
    app.run(debug=True, port=5001)