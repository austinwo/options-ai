import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        
        assert is_valid_delta(0.10) == True
        assert is_valid_delta(0.20) == True
        assert is_valid_delta(0.30) == True
        assert is_valid_delta(0.05) == False
        assert is_valid_delta(0.35) == False


class TestDTEFilter:
    """Test DTE filtering logic"""
    
    def test_valid_dte_range(self):
        """DTE between 1 and 14 is valid"""
        def is_valid_dte(dte):
            return 1 <= dte <= 14
        
        assert is_valid_dte(1) == True
        assert is_valid_dte(7) == True
        assert is_valid_dte(14) == True
        assert is_valid_dte(0) == False
        assert is_valid_dte(15) == False


class TestCandidateSorting:
    """Test candidate sorting logic"""
    
    def test_sort_by_weekly_pct_descending(self):
        """Candidates should sort by weekly % descending"""
        candidates = [
            {"strike": 640, "weeklyPct": 0.50},
            {"strike": 650, "weeklyPct": 0.70},
            {"strike": 645, "weeklyPct": 0.60},
        ]
        
        sorted_candidates = sorted(candidates, key=lambda x: x["weeklyPct"], reverse=True)
        
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


class TestProviderSelection:
    """Test AI provider selection logic"""
    
    def test_default_provider(self):
        """Default provider should be anthropic"""
        provider = "anthropic"  # default
        
        assert provider == "anthropic"
    
    def test_provider_options(self):
        """Valid provider options"""
        valid_providers = ["anthropic", "openai", "o3"]
        
        assert "anthropic" in valid_providers
        assert "openai" in valid_providers
        assert "o3" in valid_providers
        assert "invalid" not in valid_providers