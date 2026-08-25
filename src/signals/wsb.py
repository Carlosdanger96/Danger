"""
WallStreetBets signal processing for Project DEGENERATE.

Monitors WSB for ticker mentions, sentiment, and momentum.
"""

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from src.config import init_config
from src.models import (
    SignalDirection,
    SignalSource,
    TradeSignal,
    WSBMentionData,
    WSBSignal,
)
from src.signals.base import BaseSignalGenerator, SignalNormalizer, SignalScorer

logger = logging.getLogger(__name__)


# =============================================================================
# WSB Text Analyzer
# =============================================================================

class WSBTextAnalyzer:
    """Analyzes WSB posts and comments for trading signals."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.meme_terms = set(self.config.signal_sources.wsb.meme_terms)
    
    def extract_tickers(self, text: str) -> list[str]:
        """
        Extract stock tickers from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of extracted ticker symbols
        """
        tickers = set()
        
        # Pattern 1: $TICKER
        matches = re.findall(r'\$([A-Z]{1,5})', text)
        tickers.update(matches)
        
        # Pattern 2: TICKER (capitalized, 2-5 letters, standalone)
        # Exclude common words
        exclude_words = {
            "I", "AM", "PM", "A", "THE", "AND", "OR", "FOR", "TO", "IN", "ON",
            "AT", "BY", "OF", "IS", "IT", "AS", "BE", "WE", "HE", "SHE", "THEY",
        }
        matches = re.findall(r'\b([A-Z]{2,5})\b', text)
        for match in matches:
            if match not in exclude_words and not match.isdigit():
                tickers.add(match)
        
        # Pattern 3: (TICKER)
        matches = re.findall(r'\(([A-Z]{1,5})\)', text)
        tickers.update(matches)
        
        # Pattern 4: Common stock suffixes
        matches = re.findall(r'([A-Z]{1,5})[\s\W](?:stock|shares?|common|inc|corp)', text, re.IGNORECASE)
        tickers.update(matches)
        
        return sorted(list(tickers))
    
    def count_meme_terms(self, text: str) -> int:
        """
        Count occurrences of meme terms in text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Number of meme term occurrences
        """
        text_lower = text.lower()
        count = 0
        for term in self.meme_terms:
            count += text_lower.count(term.lower())
        return count
    
    def calculate_sentiment(self, text: str) -> tuple[float, float]:
        """
        Calculate bullish and bearish sentiment scores.
        
        Args:
            text: The text to analyze
            
        Returns:
            Tuple of (bullish_score, bearish_score)
        """
        text_lower = text.lower()
        
        # Bullish terms
        bullish_terms = [
            "buy", "bullish", "long", "calls", "moon", "rocket", "squeeze",
            "up", "higher", "rising", "growing", "to the moon", "tendies",
            "diamond hands", "hold", "YOLO", "all in", "10 bagger",
        ]
        
        # Bearish terms
        bearish_terms = [
            "sell", "bearish", "short", "puts", "down", "lower",
            "falling", "crashing", "dump", "bagholder", "rekt",
            "paper hands", "exit", "get out", "short squeeze",
        ]
        
        bullish_count = sum(text_lower.count(term) for term in bullish_terms)
        bearish_count = sum(text_lower.count(term) for term in bearish_terms)
        
        # Normalize by text length
        text_length = len(text_lower.split())
        if text_length == 0:
            return 0.0, 0.0
        
        bullish_score = min(bullish_count / text_length, 1.0)
        bearish_score = min(bearish_count / text_length, 1.0)
        
        return bullish_score, bearish_score
    
    def calculate_option_activity(self, text: str) -> tuple[int, int, list[float]]:
        """
        Calculate option-related activity from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Tuple of (call_mentions, put_mentions, strike_mentions)
        """
        text_lower = text.lower()
        
        call_mentions = text_lower.count("call") + text_lower.count("calls")
        put_mentions = text_lower.count("put") + text_lower.count("puts")
        
        # Extract strike prices
        strike_pattern = r'\$?\d{1,3}(?:\.\d{1,2})?(?:[kKmM])?'
        strike_matches = re.findall(strike_pattern, text)
        strikes = []
        for match in strike_matches:
            try:
                # Convert to float
                if 'k' in match.lower():
                    val = float(match.lower().replace('k', '')) * 1000
                elif 'm' in match.lower():
                    val = float(match.lower().replace('m', '')) * 1000000
                else:
                    val = float(match.replace('$', ''))
                strikes.append(val)
            except ValueError:
                continue
        
        return call_mentions, put_mentions, strikes


# =============================================================================
# WSB Data Fetcher
# =============================================================================

class WSBDataFetcher:
    """
    Fetches data from WallStreetBets subreddit.
    
    Note: Reddit API access requires proper authentication and
    respect for rate limits and usage policies.
    """
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.subreddit = self.config.signal_sources.wsb.subreddit
        self.lookback_minutes = self.config.signal_sources.wsb.lookback_minutes
        self.acceleration_window = self.config.signal_sources.wsb.acceleration_window
    
    def fetch_recent_posts(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Fetch recent posts from WSB.
        
        Args:
            limit: Maximum number of posts to fetch
            
        Returns:
            List of post data
        """
        # Placeholder - would integrate with Reddit API (PRAW)
        # For now, return empty list
        return []
    
    def fetch_post_comments(self, post_id: str, limit: int = 500) -> list[dict[str, Any]]:
        """
        Fetch comments for a specific post.
        
        Args:
            post_id: The post ID
            limit: Maximum number of comments to fetch
            
        Returns:
            List of comment data
        """
        # Placeholder - would integrate with Reddit API
        return []
    
    def get_hot_posts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get hot posts from WSB."""
        # Placeholder
        return []
    
    def get_new_posts(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get new posts from WSB."""
        # Placeholder
        return []


# =============================================================================
# WSB Analyzer
# =============================================================================

class WSBAnalyzer:
    """Analyzes WSB data and extracts trading signals."""
    
    def __init__(self, config: Any = None):
        self.config = config or init_config()
        self.text_analyzer = WSBTextAnalyzer(config)
        self.fetcher = WSBDataFetcher(config)
        
        # Track mention history
        self.mention_history: dict[str, list[tuple[datetime, int]]] = defaultdict(list)
    
    def analyze_post(self, post: dict[str, Any]) -> list[tuple[str, WSBMentionData]]:
        """
        Analyze a single WSB post.
        
        Args:
            post: The post data
            
        Returns:
            List of (ticker, WSBMentionData) tuples
        """
        results = []
        
        text = post.get("title", "") + "\n" + post.get("selftext", "")
        score = post.get("score", 0)
        created_utc = datetime.utcfromtimestamp(post.get("created_utc", 0))
        
        # Extract tickers
        tickers = self.text_analyzer.extract_tickers(text)
        
        for ticker in tickers:
            # Count mentions
            mention_count = text.upper().count(ticker)
            
            # Calculate sentiment
            bullish, bearish = self.text_analyzer.calculate_sentiment(text)
            
            # Count meme terms
            meme_count = self.text_analyzer.count_meme_terms(text)
            
            # Count option activity
            calls, puts, strikes = self.text_analyzer.calculate_option_activity(text)
            
            # Create mention data
            mention_data = WSBMentionData(
                ticker=ticker,
                post_score=score,
                bullish_language=bullish,
                bearish_language=bearish,
                option_mentions=calls + puts,
                strike_mentions=strikes,
                meme_intensity=meme_count,
            )
            
            results.append((ticker, mention_data))
        
        return results
    
    def analyze_comment(self, comment: dict[str, Any]) -> list[tuple[str, WSBMentionData]]:
        """
        Analyze a single WSB comment.
        
        Args:
            comment: The comment data
            
        Returns:
            List of (ticker, WSBMentionData) tuples
        """
        results = []
        
        text = comment.get("body", "")
        score = comment.get("score", 0)
        created_utc = datetime.utcfromtimestamp(comment.get("created_utc", 0))
        
        # Extract tickers
        tickers = self.text_analyzer.extract_tickers(text)
        
        for ticker in tickers:
            # Count mentions
            mention_count = text.upper().count(ticker)
            
            # Calculate sentiment
            bullish, bearish = self.text_analyzer.calculate_sentiment(text)
            
            # Count meme terms
            meme_count = self.text_analyzer.count_meme_terms(text)
            
            # Count option activity
            calls, puts, strikes = self.text_analyzer.calculate_option_activity(text)
            
            # Create mention data
            mention_data = WSBMentionData(
                ticker=ticker,
                post_score=score,
                bullish_language=bullish,
                bearish_language=bearish,
                option_mentions=calls + puts,
                strike_mentions=strikes,
                meme_intensity=meme_count,
            )
            
            results.append((ticker, mention_data))
        
        return results
    
    def calculate_mention_acceleration(self, ticker: str) -> float:
        """
        Calculate mention acceleration for a ticker.
        
        Args:
            ticker: The ticker to analyze
            
        Returns:
            Acceleration score (0-1)
        """
        if ticker not in self.mention_history or len(self.mention_history[ticker]) < 2:
            return 0.0
        
        history = self.mention_history[ticker]
        
        # Get recent mentions
        now = datetime.utcnow()
        recent = [
            count for timestamp, count in history
            if now - timestamp <= timedelta(minutes=self.config.signal_sources.wsb.acceleration_window)
        ]
        
        if len(recent) < 2:
            return 0.0
        
        # Calculate acceleration (rate of change of mentions)
        # Simple approach: compare current to previous
        if len(recent) >= 2:
            current = recent[-1]
            previous = recent[-2]
            if previous > 0:
                acceleration = (current - previous) / previous
                return min(max(acceleration, 0.0), 1.0)
        
        return 0.0
    
    def calculate_wsb_score(
        self,
        ticker: str,
        mention_data: WSBMentionData,
    ) -> float:
        """
        Calculate WSB_SCORE for a ticker.
        
        WSB_SCORE =
            0.30 * MentionAcceleration
            + 0.20 * EngagementVelocity
            + 0.20 * SentimentExtremity
            + 0.15 * PriceMomentum
            + 0.10 * OptionActivity
            + 0.05 * MemeIntensity
        
        Args:
            ticker: The ticker
            mention_data: The mention data
            
        Returns:
            WSB score (0-1)
        """
        # Mention acceleration
        acceleration = self.calculate_mention_acceleration(ticker)
        
        # Engagement velocity (score / time)
        # Simplified: use post score as proxy
        engagement = min(mention_data.post_score / 1000, 1.0) if mention_data.post_score > 0 else 0.0
        
        # Sentiment extremity (max of bullish or bearish)
        sentiment = max(mention_data.bullish_language, mention_data.bearish_language)
        
        # Price momentum (placeholder - would need price data)
        price_momentum = 0.5
        
        # Option activity
        option_activity = min(mention_data.option_mentions / 10, 1.0)
        
        # Meme intensity
        meme_intensity = min(mention_data.meme_intensity / 5, 1.0)
        
        score = (
            0.30 * acceleration
            + 0.20 * engagement
            + 0.20 * sentiment
            + 0.15 * price_momentum
            + 0.10 * option_activity
            + 0.05 * meme_intensity
        )
        
        return min(max(score, 0.0), 1.0)


# =============================================================================
# WSB Signal Generator
# =============================================================================

class WSBSignalGenerator(BaseSignalGenerator):
    """Generates trading signals from WSB data."""
    
    def __init__(self, config: Any = None):
        super().__init__(SignalSource.WSB)
        self.config = config or init_config()
        self.analyzer = WSBAnalyzer(config)
        self.fetcher = WSBDataFetcher(config)
        
        # Track processed posts/comments
        self.processed_ids: set[str] = set()
        
        # Aggregate mention data
        self.mention_aggregator: dict[str, WSBMentionData] = {}
    
    def process_post(self, post: dict[str, Any]) -> list[TradeSignal]:
        """
        Process a WSB post into signals.
        
        Args:
            post: The post data
            
        Returns:
            List of TradeSignals
        """
        post_id = post.get("id", "")
        if post_id in self.processed_ids:
            return []
        
        self.processed_ids.add(post_id)
        
        # Analyze post
        post_results = self.analyzer.analyze_post(post)
        
        signals = []
        for ticker, mention_data in post_results:
            # Aggregate mention data
            if ticker not in self.mention_aggregator:
                self.mention_aggregator[ticker] = WSBMentionData(ticker=ticker)
            
            # Update aggregator
            self.mention_aggregator[ticker].mentions_15m += 1
            self.mention_aggregator[ticker].mentions_1h += 1
            self.mention_aggregator[ticker].mentions_24h += 1
            self.mention_aggregator[ticker].post_score = max(
                self.mention_aggregator[ticker].post_score,
                mention_data.post_score
            )
            self.mention_aggregator[ticker].bullish_language = max(
                self.mention_aggregator[ticker].bullish_language,
                mention_data.bullish_language
            )
            self.mention_aggregator[ticker].bearish_language = max(
                self.mention_aggregator[ticker].bearish_language,
                mention_data.bearish_language
            )
            self.mention_aggregator[ticker].option_mentions += mention_data.option_mentions
            self.mention_aggregator[ticker].meme_intensity += mention_data.meme_intensity
            
            # Calculate score
            score = self.analyzer.calculate_wsb_score(ticker, self.mention_aggregator[ticker])
            
            # Determine direction based on sentiment
            if self.mention_aggregator[ticker].bullish_language > self.mention_aggregator[ticker].bearish_language:
                direction = SignalDirection.CALL
            else:
                direction = SignalDirection.PUT
            
            # Calculate urgency
            urgency = self._calculate_urgency(self.mention_aggregator[ticker])
            
            # Create signal
            signal = SignalNormalizer.normalize_to_trade_signal(
                source=SignalSource.WSB,
                ticker=ticker,
                direction=direction,
                confidence=score,
                urgency=urgency,
                timestamp=datetime.utcnow(),
                metadata={
                    "mention_count": self.mention_aggregator[ticker].mentions_15m,
                    "post_score": self.mention_aggregator[ticker].post_score,
                    "bullish_sentiment": self.mention_aggregator[ticker].bullish_language,
                    "bearish_sentiment": self.mention_aggregator[ticker].bearish_language,
                    "meme_intensity": self.mention_aggregator[ticker].meme_intensity,
                },
            )
            
            signals.append(signal)
        
        return signals
    
    def process_comment(self, comment: dict[str, Any]) -> list[TradeSignal]:
        """
        Process a WSB comment into signals.
        
        Args:
            comment: The comment data
            
        Returns:
            List of TradeSignals
        """
        comment_id = comment.get("id", "")
        if comment_id in self.processed_ids:
            return []
        
        self.processed_ids.add(comment_id)
        
        # Analyze comment
        comment_results = self.analyzer.analyze_comment(comment)
        
        signals = []
        for ticker, mention_data in comment_results:
            # Aggregate mention data
            if ticker not in self.mention_aggregator:
                self.mention_aggregator[ticker] = WSBMentionData(ticker=ticker)
            
            # Update aggregator
            self.mention_aggregator[ticker].mentions_15m += 1
            self.mention_aggregator[ticker].mentions_1h += 1
            self.mention_aggregator[ticker].mentions_24h += 1
            self.mention_aggregator[ticker].comment_velocity += 1
            self.mention_aggregator[ticker].bullish_language = max(
                self.mention_aggregator[ticker].bullish_language,
                mention_data.bullish_language
            )
            self.mention_aggregator[ticker].bearish_language = max(
                self.mention_aggregator[ticker].bearish_language,
                mention_data.bearish_language
            )
            self.mention_aggregator[ticker].option_mentions += mention_data.option_mentions
            self.mention_aggregator[ticker].meme_intensity += mention_data.meme_intensity
            
            # Calculate score
            score = self.analyzer.calculate_wsb_score(ticker, self.mention_aggregator[ticker])
            
            # Determine direction based on sentiment
            if self.mention_aggregator[ticker].bullish_language > self.mention_aggregator[ticker].bearish_language:
                direction = SignalDirection.CALL
            else:
                direction = SignalDirection.PUT
            
            # Calculate urgency
            urgency = self._calculate_urgency(self.mention_aggregator[ticker])
            
            # Create signal
            signal = SignalNormalizer.normalize_to_trade_signal(
                source=SignalSource.WSB,
                ticker=ticker,
                direction=direction,
                confidence=score,
                urgency=urgency,
                timestamp=datetime.utcnow(),
                metadata={
                    "mention_count": self.mention_aggregator[ticker].mentions_15m,
                    "comment_velocity": self.mention_aggregator[ticker].comment_velocity,
                    "bullish_sentiment": self.mention_aggregator[ticker].bullish_language,
                    "bearish_sentiment": self.mention_aggregator[ticker].bearish_language,
                    "meme_intensity": self.mention_aggregator[ticker].meme_intensity,
                },
            )
            
            signals.append(signal)
        
        return signals
    
    def _calculate_urgency(self, mention_data: WSBMentionData) -> float:
        """
        Calculate urgency score based on mention data.
        
        Args:
            mention_data: The aggregated mention data
            
        Returns:
            Urgency score (0-1)
        """
        # Base urgency from mention count
        mention_count = mention_data.mentions_15m + mention_data.mentions_1h
        
        # Normalize (cap at 100 mentions)
        mention_urgency = min(mention_count / 100, 1.0)
        
        # Boost for high sentiment
        sentiment = max(mention_data.bullish_language, mention_data.bearish_language)
        sentiment_boost = sentiment * 0.2
        
        # Boost for meme intensity
        meme_boost = min(mention_data.meme_intensity / 10, 1.0) * 0.1
        
        urgency = mention_urgency + sentiment_boost + meme_boost
        
        return min(urgency, 1.0)
    
    def generate_signals(self) -> list[TradeSignal]:
        """Generate signals from recent WSB data."""
        signals = []
        
        # Fetch recent posts
        posts = self.fetcher.fetch_recent_posts(limit=50)
        for post in posts:
            signals.extend(self.process_post(post))
        
        # Fetch comments for hot posts
        hot_posts = self.fetcher.get_hot_posts(limit=20)
        for post in hot_posts:
            comments = self.fetcher.fetch_post_comments(post.get("id", ""), limit=200)
            for comment in comments:
                signals.extend(self.process_comment(comment))
        
        return self.score_and_filter(signals)
    
    def get_latest_signal(self, ticker: str | None = None) -> TradeSignal | None:
        """Get the latest signal."""
        signals = self.generate_signals()
        
        if ticker:
            signals = [s for s in signals if s.ticker == ticker]
        
        if signals:
            return max(signals, key=lambda x: x.timestamp)
        return None
    
    def clear_cache(self) -> None:
        """Clear processed IDs and mention aggregator."""
        self.processed_ids.clear()
        self.mention_aggregator.clear()


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "WSBTextAnalyzer",
    "WSBDataFetcher",
    "WSBAnalyzer",
    "WSBSignalGenerator",
]
