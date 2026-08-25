"""
Black-Scholes Greeks calculation for Project DEGENERATE.

Provides accurate Greeks calculation for option pricing and analysis.
"""

import math
from typing import Tuple

from src.models import OptionType


# =============================================================================
# Black-Scholes Implementation
# =============================================================================

class BlackScholes:
    """
    Black-Scholes option pricing model.
    
    Calculates option prices and Greeks (delta, gamma, theta, vega, rho).
    """
    
    def __init__(self, risk_free_rate: float = 0.05, dividend_yield: float = 0.0):
        """
        Initialize Black-Scholes model.
        
        Args:
            risk_free_rate: Annual risk-free interest rate (decimal)
            dividend_yield: Annual dividend yield (decimal)
        """
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield
    
    @staticmethod
    def cumulative_normal(x: float) -> float:
        """
        Cumulative normal distribution function.
        
        Args:
            x: Value at which to evaluate CDF
            
        Returns:
            P(X <= x) for standard normal distribution
        """
        # Abramowitz and Stegun approximation
        if x < -8.0:
            return 0.0
        elif x > 8.0:
            return 1.0
        
        a1 = 0.319381530
        a2 = -0.356563782
        a3 = 1.781477937
        a4 = -1.821255978
        a5 = 1.330274429
        
        p = 0.2316419
        
        sign = 1 if x >= 0 else -1
        x = abs(x)
        
        t = 1.0 / (1.0 + p * x)
        
        y = 1.0 - ((
            (((a5 * t + a4) * t + a3) * t + a2) * t + a1
        ) * t * math.exp(-x * x / 2.0))
        
        return 0.5 * (1.0 + sign * y)
    
    @staticmethod
    def normal_density(x: float) -> float:
        """
        Standard normal probability density function.
        
        Args:
            x: Value at which to evaluate PDF
            
        Returns:
            PDF value at x
        """
        return math.exp(-x * x / 2.0) / math.sqrt(2.0 * math.pi)
    
    def d1(
        self,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """
        Calculate d1 parameter for Black-Scholes.
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (decimal)
            
        Returns:
            d1 value
        """
        if volatility <= 0 or time_to_expiry <= 0:
            return 0.0
        
        adjusted_forward = underlying * math.exp(
            (self.risk_free_rate - self.dividend_yield) * time_to_expiry
        )
        
        numerator = math.log(adjusted_forward / strike) + (volatility ** 2) * time_to_expiry / 2.0
        denominator = volatility * math.sqrt(time_to_expiry)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def d2(
        self,
        d1: float,
        volatility: float,
        time_to_expiry: float,
    ) -> float:
        """
        Calculate d2 parameter for Black-Scholes.
        
        Args:
            d1: d1 value
            volatility: Implied volatility
            time_to_expiry: Time to expiry in years
            
        Returns:
            d2 value
        """
        if volatility <= 0 or time_to_expiry <= 0:
            return 0.0
        return d1 - volatility * math.sqrt(time_to_expiry)
    
    def call_price(
        self,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """
        Calculate call option price using Black-Scholes.
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (decimal)
            
        Returns:
            Call option price
        """
        if volatility <= 0 or time_to_expiry <= 0 or underlying <= 0 or strike <= 0:
            return 0.0
        
        d1_val = self.d1(underlying, strike, time_to_expiry, volatility)
        d2_val = self.d2(d1_val, volatility, time_to_expiry)
        
        adjusted_forward = underlying * math.exp(
            (self.risk_free_rate - self.dividend_yield) * time_to_expiry
        )
        
        call_price = (
            adjusted_forward * self.cumulative_normal(d1_val)
            - strike * math.exp(-self.risk_free_rate * time_to_expiry) * self.cumulative_normal(d2_val)
        )
        
        return max(call_price, 0.0)
    
    def put_price(
        self,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """
        Calculate put option price using Black-Scholes.
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (decimal)
            
        Returns:
            Put option price
        """
        if volatility <= 0 or time_to_expiry <= 0 or underlying <= 0 or strike <= 0:
            return 0.0
        
        d1_val = self.d1(underlying, strike, time_to_expiry, volatility)
        d2_val = self.d2(d1_val, volatility, time_to_expiry)
        
        adjusted_forward = underlying * math.exp(
            (self.risk_free_rate - self.dividend_yield) * time_to_expiry
        )
        
        put_price = (
            strike * math.exp(-self.risk_free_rate * time_to_expiry) * self.cumulative_normal(-d2_val)
            - adjusted_forward * self.cumulative_normal(-d1_val)
        )
        
        return max(put_price, 0.0)
    
    def option_price(
        self,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        option_type: OptionType,
    ) -> float:
        """
        Calculate option price based on type.
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility (decimal)
            option_type: CALL or PUT
            
        Returns:
            Option price
        """
        if option_type == OptionType.CALL:
            return self.call_price(underlying, strike, time_to_expiry, volatility)
        else:
            return self.put_price(underlying, strike, time_to_expiry, volatility)


# =============================================================================
# Greeks Calculation
# =============================================================================

class GreeksCalculator:
    """
    Calculates option Greeks using Black-Scholes.
    
    Provides delta, gamma, theta, vega, and rho calculations.
    """
    
    def __init__(self, risk_free_rate: float = 0.05, dividend_yield: float = 0.0, days_per_year: int = 365):
        """
        Initialize Greeks calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate
            dividend_yield: Annual dividend yield
            days_per_year: Days in a year for time calculations
        """
        self.bs = BlackScholes(risk_free_rate, dividend_yield)
        self.days_per_year = days_per_year
    
    def calculate_all_greeks(
        self,
        underlying: float,
        strike: float,
        dte: int,
        iv: float,
        option_type: OptionType,
    ) -> dict[str, float]:
        """
        Calculate all Greeks for an option.
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            dte: Days to expiration
            iv: Implied volatility (decimal)
            option_type: CALL or PUT
            
        Returns:
            Dictionary with all Greeks
        """
        tte = dte / self.days_per_year  # Time to expiry in years
        
        return {
            "delta": self.delta(underlying, strike, tte, iv, option_type),
            "gamma": self.gamma(underlying, strike, tte, iv),
            "theta": self.theta(underlying, strike, tte, iv, option_type),
            "vega": self.vega(underlying, strike, tte, iv),
            "rho": self.rho(underlying, strike, tte, iv, option_type),
        }
    
    def delta(
        self,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        option_type: OptionType,
    ) -> float:
        """
        Calculate delta (sensitivity to underlying price).
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility
            option_type: CALL or PUT
            
        Returns:
            Delta value (0-1 for calls, -1-0 for puts)
        """
        if volatility <= 0 or time_to_expiry <= 0 or underlying <= 0 or strike <= 0:
            return 0.0
        
        d1_val = self.bs.d1(underlying, strike, time_to_expiry, volatility)
        
        if option_type == OptionType.CALL:
            return self.bs.cumulative_normal(d1_val)
        else:
            return self.bs.cumulative_normal(d1_val) - 1.0
    
    def gamma(
        self,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """
        Calculate gamma (rate of change of delta).
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility
            
        Returns:
            Gamma value
        """
        if volatility <= 0 or time_to_expiry <= 0 or underlying <= 0 or strike <= 0:
            return 0.0
        
        d1_val = self.bs.d1(underlying, strike, time_to_expiry, volatility)
        
        adjusted_forward = underlying * math.exp(
            (self.bs.risk_free_rate - self.bs.dividend_yield) * time_to_expiry
        )
        
        return (
            self.bs.normal_density(d1_val)
            / (adjusted_forward * volatility * math.sqrt(time_to_expiry))
        )
    
    def theta(
        self,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        option_type: OptionType,
    ) -> float:
        """
        Calculate theta (time decay).
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility
            option_type: CALL or PUT
            
        Returns:
            Theta value (negative for both calls and puts)
        """
        if volatility <= 0 or time_to_expiry <= 0 or underlying <= 0 or strike <= 0:
            return 0.0
        
        d1_val = self.bs.d1(underlying, strike, time_to_expiry, volatility)
        d2_val = self.bs.d2(d1_val, volatility, time_to_expiry)
        
        adjusted_forward = underlying * math.exp(
            (self.bs.risk_free_rate - self.bs.dividend_yield) * time_to_expiry
        )
        
        if option_type == OptionType.CALL:
            term1 = -adjusted_forward * self.bs.normal_density(d1_val) * volatility / (2 * math.sqrt(time_to_expiry))
            term2 = -self.bs.risk_free_rate * strike * math.exp(-self.bs.risk_free_rate * time_to_expiry) * self.bs.cumulative_normal(d2_val)
            term3 = self.bs.dividend_yield * adjusted_forward * self.bs.cumulative_normal(d1_val)
            return (term1 + term2 + term3) / self.days_per_year
        else:  # PUT
            term1 = -adjusted_forward * self.bs.normal_density(d1_val) * volatility / (2 * math.sqrt(time_to_expiry))
            term2 = self.bs.risk_free_rate * strike * math.exp(-self.bs.risk_free_rate * time_to_expiry) * self.bs.cumulative_normal(-d2_val)
            term3 = -self.bs.dividend_yield * adjusted_forward * self.bs.cumulative_normal(-d1_val)
            return (term1 + term2 + term3) / self.days_per_year
    
    def vega(
        self,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
    ) -> float:
        """
        Calculate vega (sensitivity to volatility).
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility
            
        Returns:
            Vega value
        """
        if volatility <= 0 or time_to_expiry <= 0 or underlying <= 0 or strike <= 0:
            return 0.0
        
        d1_val = self.bs.d1(underlying, strike, time_to_expiry, volatility)
        
        adjusted_forward = underlying * math.exp(
            (self.bs.risk_free_rate - self.bs.dividend_yield) * time_to_expiry
        )
        
        return (
            adjusted_forward
            * self.bs.normal_density(d1_val)
            * math.sqrt(time_to_expiry)
            / 100  # Convert to per 1% change in volatility
        )
    
    def rho(
        self,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        option_type: OptionType,
    ) -> float:
        """
        Calculate rho (sensitivity to interest rates).
        
        Args:
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility
            option_type: CALL or PUT
            
        Returns:
            Rho value
        """
        if volatility <= 0 or time_to_expiry <= 0 or underlying <= 0 or strike <= 0:
            return 0.0
        
        d1_val = self.bs.d1(underlying, strike, time_to_expiry, volatility)
        d2_val = self.bs.d2(d1_val, volatility, time_to_expiry)
        
        adjusted_forward = underlying * math.exp(
            (self.bs.risk_free_rate - self.bs.dividend_yield) * time_to_expiry
        )
        
        if option_type == OptionType.CALL:
            return (
                strike
                * time_to_expiry
                * math.exp(-self.bs.risk_free_rate * time_to_expiry)
                * self.bs.cumulative_normal(d2_val)
                / 100  # Convert to per 1% change in interest rate
            )
        else:  # PUT
            return (
                -strike
                * time_to_expiry
                * math.exp(-self.bs.risk_free_rate * time_to_expiry)
                * self.bs.cumulative_normal(-d2_val)
                / 100
            )


# =============================================================================
# Implied Volatility Calculation
# =============================================================================

class ImpliedVolatilityCalculator:
    """
    Calculates implied volatility using Newton-Raphson method.
    """
    
    def __init__(self, max_iterations: int = 100, tolerance: float = 1e-6):
        """
        Initialize IV calculator.
        
        Args:
            max_iterations: Maximum iterations for Newton-Raphson
            tolerance: Convergence tolerance
        """
        self.bs = BlackScholes()
        self.max_iterations = max_iterations
        self.tolerance = tolerance
    
    def calculate_iv(
        self,
        market_price: float,
        underlying: float,
        strike: float,
        time_to_expiry: float,
        option_type: OptionType,
        initial_guess: float = 0.5,
    ) -> float:
        """
        Calculate implied volatility using Newton-Raphson.
        
        Args:
            market_price: Current market price of option
            underlying: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiry in years
            option_type: CALL or PUT
            initial_guess: Initial IV guess (0.5 = 50%)
            
        Returns:
            Implied volatility (decimal)
        """
        if market_price <= 0 or underlying <= 0 or strike <= 0 or time_to_expiry <= 0:
            return 0.0
        
        # Initial guess
        volatility = initial_guess
        
        for _ in range(self.max_iterations):
            # Calculate theoretical price
            theoretical_price = self.bs.option_price(
                underlying, strike, time_to_expiry, volatility, option_type
            )
            
            # Calculate vega
            vega = GreeksCalculator().vega(underlying, strike, time_to_expiry, volatility)
            
            if vega == 0:
                break
            
            # Calculate difference
            difference = market_price - theoretical_price
            
            # Update volatility
            volatility_update = difference / vega
            volatility += volatility_update
            
            # Check convergence
            if abs(difference) < self.tolerance:
                break
        
        return max(volatility, 0.0)


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "BlackScholes",
    "GreeksCalculator",
    "ImpliedVolatilityCalculator",
]
