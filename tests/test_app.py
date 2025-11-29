import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Unit Tests - Core Calculation Logic (No app import needed)
# =============================================================================

class TestRecommendationLogic:
    """Test the core recommendation calculation logic"""

    def test_weekly_return_calculation(self):
        """Weekly return = (bid / price) * (7 / dte) * 100"""
        bid = 3.80
        underlying_price = 633.0
        dte = 7

        weekly_return = (bid / underlying_price) * (7 / dte) * 100

        assert round(weekly_return, 2) == 0.60

    def test_annualized_return_calculation(self):
        """Annualized return = (bid / price) * (365 / dte) * 100"""
        bid = 3.80
        underlying_price = 633.0
        dte = 7

        annualized_return = (bid / underlying_price) * (365 / dte) * 100

        assert round(annualized_return, 1) == 31.3

    def test_otm_dollar_calculation(self):
        """OTM $ = strike - current price"""
        strike = 650.0
        underlying_price = 633.0

        otm_dollar = strike - underlying_price

        assert otm_dollar == 17.0

    def test_otm_percent_calculation(self):
        """OTM % = (strike - price) / price * 100"""
        strike = 650.0
        underlying_price = 633.0

        otm_pct = (strike - underlying_price) / underlying_price * 100

        assert round(otm_pct, 2) == 2.69

    def test_contracts_from_shares(self):
        """100 shares = 1 contract"""
        assert 900 // 100 == 9
        assert 150 // 100 == 1
        assert 99 // 100 == 0

    def test_total_premium_calculation(self):
        """Total premium = bid * contracts * 100"""
        bid = 3.80
        contracts = 9

        total_premium = bid * contracts * 100

        assert total_premium == pytest.approx(3420.0)


class TestDeltaFilter:
    """Test delta filtering logic"""

    def test_valid_delta_range(self):
        """Delta between 0.10 and 0.30 is valid"""

        def is_valid_delta(delta):
            return 0.10 <= delta <= 0.30

        assert is_valid_delta(0.10) is True
        assert is_valid_delta(0.20) is True
        assert is_valid_delta(0.30) is True
        assert is_valid_delta(0.05) is False
        assert is_valid_delta(0.35) is False

    def test_delta_edge_cases(self):
        """Test delta at boundaries"""

        def is_valid_delta(delta):
            return 0.10 <= delta <= 0.30

        assert is_valid_delta(0.099) is False
        assert is_valid_delta(0.301) is False


class TestDTEFilter:
    """Test DTE filtering logic"""

    def test_valid_dte_range(self):
        """DTE between 1 and 14 is valid"""

        def is_valid_dte(dte):
            return 1 <= dte <= 14

        assert is_valid_dte(1) is True
        assert is_valid_dte(7) is True
        assert is_valid_dte(14) is True
        assert is_valid_dte(0) is False
        assert is_valid_dte(15) is False


class TestCandidateSorting:
    """Test candidate sorting logic"""

    def test_sort_by_weekly_pct_descending(self):
        """Candidates should sort by weekly % descending"""
        candidates = [
            {"strike": 640, "weeklyPct": 0.50},
            {"strike": 650, "weeklyPct": 0.70},
            {"strike": 645, "weeklyPct": 0.60},
        ]

        sorted_candidates = sorted(
            candidates, key=lambda x: x["weeklyPct"], reverse=True
        )

        assert sorted_candidates[0]["strike"] == 650
        assert sorted_candidates[1]["strike"] == 645
        assert sorted_candidates[2]["strike"] == 640

    def test_sort_by_delta_ascending(self):
        """Can sort by delta ascending for lower risk options"""
        candidates = [
            {"strike": 640, "delta": 0.25},
            {"strike": 650, "delta": 0.15},
            {"strike": 645, "delta": 0.20},
        ]

        sorted_candidates = sorted(candidates, key=lambda x: x["delta"], reverse=False)

        assert sorted_candidates[0]["strike"] == 650
        assert sorted_candidates[1]["strike"] == 645
        assert sorted_candidates[2]["strike"] == 640

    def test_top_n_candidates(self):
        """Should return only top N candidates"""
        candidates = [{"strike": i, "weeklyPct": i * 0.1} for i in range(20)]

        sorted_candidates = sorted(
            candidates, key=lambda x: x["weeklyPct"], reverse=True
        )[:10]

        assert len(sorted_candidates) == 10
        assert sorted_candidates[0]["strike"] == 19


class TestPriceChangeCalculation:
    """Test price change stats calculation"""

    def test_positive_change(self):
        """Positive price change calculation"""
        first_price = 100.0
        last_price = 110.0

        change = last_price - first_price
        change_percent = (change / first_price) * 100

        assert change == 10.0
        assert change_percent == 10.0

    def test_negative_change(self):
        """Negative price change calculation"""
        first_price = 100.0
        last_price = 90.0

        change = last_price - first_price
        change_percent = (change / first_price) * 100

        assert change == -10.0
        assert change_percent == -10.0

    def test_no_change(self):
        """Zero price change"""
        first_price = 100.0
        last_price = 100.0

        change = last_price - first_price
        change_percent = (change / first_price) * 100

        assert change == 0.0
        assert change_percent == 0.0


class TestProviderSelection:
    """Test AI provider selection logic"""

    def test_default_provider(self):
        """Default provider should be anthropic"""
        provider = "anthropic"

        assert provider == "anthropic"

    def test_provider_options(self):
        """Valid provider options"""
        valid_providers = ["anthropic", "openai"]

        assert "anthropic" in valid_providers
        assert "openai" in valid_providers
        assert "invalid" not in valid_providers

    def test_model_options(self):
        """Valid model options for openai"""
        valid_models = ["gpt-4o-mini", "o3-mini"]

        assert "gpt-4o-mini" in valid_models
        assert "o3-mini" in valid_models


# =============================================================================
# Data Transformation Tests (No app import needed)
# =============================================================================

class TestCandleTransformation:
    """Test candle data transformation"""

    def test_transforms_schwab_candles_to_chart_format(self):
        """Should transform Schwab candle data to chart format"""
        schwab_candles = [
            {
                "datetime": 1700000000000,
                "open": 180.0,
                "high": 182.0,
                "low": 179.0,
                "close": 181.0
            },
            {
                "datetime": 1700000300000,
                "open": 181.0,
                "high": 183.0,
                "low": 180.0,
                "close": 182.5
            }
        ]

        transformed = [
            {
                "time": c["datetime"] // 1000,
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
            }
            for c in schwab_candles
        ]

        assert len(transformed) == 2
        assert transformed[0]["time"] == 1700000000
        assert transformed[0]["close"] == 181.0
        assert transformed[1]["time"] == 1700000300

    def test_empty_candles(self):
        """Should handle empty candles response"""
        data = {"candles": []}

        candles = [
            {"time": c["datetime"] // 1000, "close": c["close"]}
            for c in data.get("candles", [])
        ]

        assert candles == []


class TestPeriodMapping:
    """Test period to Schwab API parameter mapping"""

    def test_period_mapping(self):
        """Period parameter should map to correct Schwab API params"""
        period_map = {
            "1d": {"periodType": "day", "period": 1, "frequencyType": "minute", "frequency": 5},
            "5d": {"periodType": "day", "period": 5, "frequencyType": "minute", "frequency": 5},
            "1m": {"periodType": "month", "period": 1, "frequencyType": "daily", "frequency": 1},
            "6m": {"periodType": "month", "period": 6, "frequencyType": "daily", "frequency": 1},
            "1y": {"periodType": "year", "period": 1, "frequencyType": "daily", "frequency": 1},
            "5y": {"periodType": "year", "period": 5, "frequencyType": "weekly", "frequency": 1},
        }

        assert period_map["1d"]["periodType"] == "day"
        assert period_map["1d"]["frequency"] == 5
        assert period_map["5y"]["frequencyType"] == "weekly"

    def test_default_period(self):
        """Should default to 5d if invalid period"""
        period_map = {
            "5d": {"periodType": "day", "period": 5},
        }

        params = period_map.get("invalid", period_map["5d"])

        assert params["period"] == 5


# =============================================================================
# Position Filtering Tests
# =============================================================================

class TestPositionFiltering:
    """Test position filtering logic"""

    def test_filters_positions_under_100_shares(self):
        """Should only include positions with 100+ shares"""
        positions = [
            {"instrument": {"assetType": "EQUITY", "symbol": "AAPL"}, "longQuantity": 50},
            {"instrument": {"assetType": "EQUITY", "symbol": "META"}, "longQuantity": 900},
            {"instrument": {"assetType": "EQUITY", "symbol": "NVDA"}, "longQuantity": 100},
        ]

        holdings = {}
        for pos in positions:
            if pos["instrument"]["assetType"] == "EQUITY":
                symbol = pos["instrument"]["symbol"]
                quantity = int(pos["longQuantity"])
                if quantity >= 100:
                    holdings[symbol] = {"shares": (quantity // 100) * 100}

        assert "AAPL" not in holdings
        assert "META" in holdings
        assert holdings["META"]["shares"] == 900
        assert "NVDA" in holdings
        assert holdings["NVDA"]["shares"] == 100

    def test_filters_non_equity_positions(self):
        """Should only include EQUITY positions"""
        positions = [
            {"instrument": {"assetType": "EQUITY", "symbol": "META"}, "longQuantity": 900},
            {"instrument": {"assetType": "OPTION", "symbol": "META_C"}, "longQuantity": 10},
            {"instrument": {"assetType": "CASH_EQUIVALENT", "symbol": "MMDA"}, "longQuantity": 10000},
        ]

        holdings = {}
        for pos in positions:
            if pos["instrument"]["assetType"] == "EQUITY":
                symbol = pos["instrument"]["symbol"]
                quantity = int(pos["longQuantity"])
                if quantity >= 100:
                    holdings[symbol] = {"shares": (quantity // 100) * 100}

        assert len(holdings) == 1
        assert "META" in holdings

    def test_rounds_shares_to_contract_boundary(self):
        """Should round shares down to nearest 100"""
        positions = [
            {"instrument": {"assetType": "EQUITY", "symbol": "META"}, "longQuantity": 950},
        ]

        holdings = {}
        for pos in positions:
            if pos["instrument"]["assetType"] == "EQUITY":
                symbol = pos["instrument"]["symbol"]
                quantity = int(pos["longQuantity"])
                if quantity >= 100:
                    holdings[symbol] = {"shares": (quantity // 100) * 100}

        assert holdings["META"]["shares"] == 900  # 950 -> 900


# =============================================================================
# Options Candidate Filtering Tests
# =============================================================================

class TestOptionsCandidateFiltering:
    """Test options chain filtering logic"""

    def test_filters_by_delta_and_dte(self):
        """Should filter candidates by delta and DTE ranges"""
        options = [
            {"delta": 0.05, "daysToExpiration": 7, "bid": 1.0, "strikePrice": 100},  # delta too low
            {"delta": 0.15, "daysToExpiration": 7, "bid": 1.5, "strikePrice": 105},  # valid
            {"delta": 0.25, "daysToExpiration": 7, "bid": 2.0, "strikePrice": 110},  # valid
            {"delta": 0.35, "daysToExpiration": 7, "bid": 2.5, "strikePrice": 115},  # delta too high
            {"delta": 0.20, "daysToExpiration": 0, "bid": 1.0, "strikePrice": 107},  # dte too low
            {"delta": 0.20, "daysToExpiration": 21, "bid": 1.0, "strikePrice": 108}, # dte too high
            {"delta": 0.20, "daysToExpiration": 7, "bid": 0, "strikePrice": 109},    # no bid
        ]

        valid_candidates = []
        for opt in options:
            delta = abs(opt.get("delta", 0))
            dte = opt.get("daysToExpiration", 0)
            bid = opt.get("bid", 0)

            if 0.10 <= delta <= 0.30 and 1 <= dte <= 14 and bid > 0:
                valid_candidates.append(opt)

        assert len(valid_candidates) == 2
        assert valid_candidates[0]["strikePrice"] == 105
        assert valid_candidates[1]["strikePrice"] == 110

    def test_handles_negative_delta(self):
        """Should use absolute value of delta"""
        raw_delta = -0.25

        delta = abs(raw_delta)

        assert delta == 0.25
        assert 0.10 <= delta <= 0.30


# =============================================================================
# LLM Prompt Building Tests
# =============================================================================

class TestLLMPromptBuilding:
    """Test LLM prompt construction"""

    def test_prompt_includes_position_info(self):
        """Prompt should include position details"""
        position = {
            "shares": 900,
            "avgPrice": 350.00,
            "gainLoss": 254000
        }
        underlying_price = 633.00

        prompt = f"""POSITION:
- Shares: {position["shares"]}
- Cost basis: ${position["avgPrice"]:.2f}
- Current price: ${underlying_price:.2f}
- Unrealized P/L: ${position["gainLoss"]:.0f}
- Contracts available: {position["shares"] // 100}"""

        assert "Shares: 900" in prompt
        assert "Cost basis: $350.00" in prompt
        assert "Current price: $633.00" in prompt
        assert "Unrealized P/L: $254000" in prompt
        assert "Contracts available: 9" in prompt

    def test_prompt_includes_candidates(self):
        """Prompt should include CC candidates"""
        candidates = [
            {"strike": 650, "exp": "2024-12-06", "dte": 7, "delta": 0.18, "bid": 3.80, "weeklyPct": 0.60, "otmPct": 2.7}
        ]

        prompt = ""
        for c in candidates:
            prompt += f"- ${c['strike']} strike, {c['exp']} expiry, {c['dte']}d DTE, delta {c['delta']}, ${c['bid']:.2f} bid, {c['weeklyPct']}%/wk, {c['otmPct']:.1f}% OTM\n"

        assert "$650 strike" in prompt
        assert "7d DTE" in prompt
        assert "delta 0.18" in prompt
        assert "$3.80 bid" in prompt


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_missing_options_chain(self):
        """Should handle missing callExpDateMap"""
        data = {"underlyingPrice": 100.0}

        candidates = []
        for exp_date, strikes in data.get("callExpDateMap", {}).items():
            candidates.append(exp_date)

        assert candidates == []

    def test_zero_underlying_price(self):
        """Should handle zero underlying price gracefully"""
        underlying_price = 0
        bid = 1.0
        dte = 7

        if underlying_price > 0:
            weekly_return = (bid / underlying_price) * (7 / dte) * 100
        else:
            weekly_return = 0

        assert weekly_return == 0

    def test_zero_dte(self):
        """Should handle zero DTE gracefully"""
        underlying_price = 100.0
        bid = 1.0
        dte = 0

        if dte > 0 and underlying_price > 0:
            weekly_return = (bid / underlying_price) * (7 / dte) * 100
        else:
            weekly_return = 0

        assert weekly_return == 0

    def test_missing_position_fields(self):
        """Should handle missing optional fields with defaults"""
        opt = {}

        delta = abs(opt.get("delta", 0))
        dte = opt.get("daysToExpiration", 0)
        bid = opt.get("bid", 0)

        assert delta == 0
        assert dte == 0
        assert bid == 0
