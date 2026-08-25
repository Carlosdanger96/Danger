# Project DEGENERATE

**Autonomous High-Convexity Options Agent**

Project DEGENERATE is an autonomous paper-trading options agent designed to pursue extremely large short-duration returns through three deliberately questionable signal systems: WallStreetBets, Pelosi Tracker, and Inverse Cramer.

## Objective

Maximize terminal account value subject only to equity remaining above the $30,000 hard floor.

- **Starting Equity**: $100,000
- **Hard Floor**: $30,000
- **Maximum Drawdown**: 70%

Sharpe ratio, volatility minimization, conventional diversification, and normal portfolio-construction principles are **intentionally not** optimization targets.

## Strategy

The system combines three signal sources with equal risk budgets:

| Sleeve | Allocation | Strategy |
|--------|------------|----------|
| WSB | 25% | Follow rapidly accelerating retail/meme conviction |
| Pelosi | 25% | Follow newly disclosed Pelosi-family securities activity using leveraged options |
| Inverse Cramer | 50% | Take the opposite side of explicit Jim Cramer directional calls |

### Signal Consensus

When independent stupidity agrees, the system creates a **Consensus Multiplier**:

- 1 source: 1.0x
- 2 sources: 1.5x
- 3 sources: 2.0x

### Contract Tiers

The agent favors high-convexity contracts:

| Tier | Delta Range | DTE Range | Description |
|------|-------------|-----------|-------------|
| TIER 1 | 0.30-0.40 | 14-45 days | Aggressive (still somewhat connected to reality) |
| TIER 2 | 0.15-0.30 | 7-21 days | Extreme (high gamma, high probability of loss) |
| TIER 3 | 0.05-0.15 | 3-14 days | Absurd (very low premium, very high probability of failure) |

The agent **disproportionately favors Tier 2 and occasionally allocates to Tier 3**.

### Position Sizing

Initial sizing based on signal confidence:

| Signal Level | Sleeve Allocation |
|--------------|-------------------|
| LOW | 5% of sleeve |
| NORMAL | 10% of sleeve |
| HIGH | 20% of sleeve |
| EXTREME | 30% of sleeve |

Example: WSB extreme signal on $25,000 sleeve = $7,500 premium risk

### Desperation Engine

Normal portfolio management reduces risk after losses. This system **intentionally does NOT**.

| Drawdown Range | Aggression Multiplier |
|----------------|----------------------|
| 0-20% | 1.0x |
| 20-40% | 1.25x |
| 40-55% | 1.50x |
| 55-65% | 1.75x |
| 65-70% | Last-Chance Mode (min 5x target multiple) |

At equity <= $30,000: **execution terminates**.

### Winner Engine

Extreme winners should be exploited:

```
$5,000 -> $10,000 (at +100%)
  - Recover approximately initial premium
  - $5,000 runner continues
  - Roll profits into higher-convexity contracts
  - Creates nonlinear compounding during major moves
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL SIGNALS                        │
├───────────────────┬──────────────────┬──────────────────────┤
│ WallStreetBets    │ Pelosi Disclosures│ Cramer Statements  │
│ posts/comments    │ + trade records   │ interviews/shows   │
└─────────┬─────────┴─────────┬────────┴──────────┬───────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────────┐
│ WSB ANALYZER   │  │ PELOSI ANALYZER│  │ CRAMER ANALYZER    │
└────────┬───────┘  └───────┬────────┘  └──────────┬─────────┘
         │                  │                      │
         ▼                  ▼                      ▼
      25% SLEEVE         25% SLEEVE             50% SLEEVE
         │                  │                      │
         └──────────────────┼──────────────────────┘
                            ▼
                 ┌──────────────────────┐
                 │ SIGNAL NORMALIZER    │
                 └──────────┬───────────┘
                            ▼
                 ┌──────────────────────┐
                 │ ABSURDITY ENGINE     │
                 └──────────┬───────────┘
                            ▼
                 ┌──────────────────────┐
                 │ OPTIONS ENGINE       │
                 └──────────┬───────────┘
                            ▼
                 ┌──────────────────────┐
                 │ DEGENERACY GOVERNOR  │
                 └──────────┬───────────┘
                            ▼
                 ┌──────────────────────┐
                 │ ALPACA MCP / API     │
                 │ PAPER TRADING        │
                 └──────────┬───────────┘
                            ▼
                 ┌──────────────────────┐
                 │ POSITION MONITOR     │
                 └──────────┬───────────┘
                            ▼
                 ┌──────────────────────┐
                 │ PERFORMANCE MEMORY   │
                 └──────────────────────┘
```

## Repository Structure

```
project-degenerate/
├── README.md
├── .env.example
├── pyproject.toml
├── config.yaml
│
├── src/
│   ├── main.py              # Main entry point
│   ├── config.py            # Configuration management
│   ├── models.py            # Data models
│   ├── database.py          # SQLite database layer
│   ├── logging.py           # Structured logging
│   ├── state.py             # Portfolio and sleeve state
│   │
│   ├── signals/
│   │   ├── base.py          # Base signal processing
│   │   ├── wsb.py           # WallStreetBets signal generator
│   │   ├── pelosi.py        # Pelosi disclosure analyzer
│   │   ├── cramer.py        # Cramer statement classifier
│   │   └── consensus.py     # Consensus engine
│   │
│   ├── analysis/
│   │   ├── sentiment.py     # Sentiment analysis
│   │   └── ticker_parser.py # Ticker extraction
│   │
│   ├── market/
│   │   ├── alpaca.py        # Alpaca API integration
│   │   ├── options.py       # Option contract scoring
│   │   ├── greeks.py        # Black-Scholes Greeks
│   │   └── equities.py      # Equity market data
│   │
│   ├── strategy/
│   │   ├── allocator.py     # Position sizing and allocation
│   │   ├── contract_selector.py # Contract selection
│   │   ├── desperation.py   # Desperation engine
│   │   ├── winner_engine.py # Winner engine
│   │   └── exits.py         # Exit strategies
│   │
│   ├── risk/
│   │   ├── governor.py      # Risk governor
│   │   ├── floor.py         # Hard floor monitoring
│   │   └── exposure.py      # Exposure management
│   │
│   ├── execution/
│   │   ├── alpaca_mcp.py    # Alpaca MCP client
│   │   ├── orders.py        # Order management
│   │   └── positions.py     # Position tracking
│   │
│   └── memory/
│       ├── trades.py        # Trade history
│       ├── signals.py       # Signal history
│       └── performance.py   # Performance tracking
│
├── data/
│   ├── signals.db
│   └── trades.db
│
├── tests/
│   ├── test_floor.py
│   ├── test_allocator.py
│   ├── test_contract_selector.py
│   └── test_signals.py
│
└── scripts/
    ├── run_agent.py
    ├── dry_run.py
    └── reset_competition.py
```

## Quick Start

### Prerequisites

- Python 3.11+
- Alpaca paper trading account (free)
- Optional: OpenAI API key for LLM-based classification

### Installation

```bash
# Clone the repository
git clone https://github.com/Carlosdanger96/Danger.git
cd Danger

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### Configuration

Edit `config.yaml` to configure:
- Sleeve allocations
- Signal thresholds
- Contract tier preferences
- Desperation engine settings

### Running the Agent

```bash
# Run once (dry run)
python scripts/dry_run.py --iterations 5

# Run continuously (paper trading)
python scripts/run_agent.py --continuous --interval 1

# Reset competition state
python scripts/reset_competition.py --confirm
```

## Implementation Phases

### Phase 1: Core Trading Infrastructure ✅
- [x] Alpaca MCP connection
- [x] Option chain retrieval
- [x] Paper option order execution
- [x] Position monitoring
- [x] SQLite logging
- [x] $30k hard floor enforcement

### Phase 2: Inverse Cramer Strategy ✅
- [x] Inverse Cramer adapter
- [x] Keyword-based recommendation classifier
- [x] Automatic contract selection
- [x] 50% sleeve allocation

### Phase 3: WSB Strategy ✅
- [x] WSB ingestion (placeholder)
- [x] Ticker extraction
- [x] Mention velocity calculation
- [x] Sentiment scoring
- [x] 25% sleeve allocation

### Phase 4: Pelosi Strategy ✅
- [x] Pelosi disclosure adapter (placeholder)
- [x] Transaction parser
- [x] Disclosure-age model
- [x] 25% sleeve allocation

### Phase 5: Advanced Features
- [ ] Consensus multiplier
- [ ] Desperation engine
- [ ] Winner compounding
- [ ] Competition dashboard

### Phase 6: Production Readiness
- [ ] 24-48 hour continuous paper simulation
- [ ] Failure testing
- [ ] API retry handling
- [ ] Duplicate-order protection
- [ ] Position reconciliation

## Important Notes

### Risk Warning

This is an **extremely high-risk** trading strategy. It is designed for **paper trading only** and intentionally violates all conventional risk management principles. The system:

- Takes concentrated positions in out-of-the-money options
- Increases position sizes as losses mount
- Has a 70% maximum drawdown tolerance
- Will lose all capital if equity falls to $30,000

**DO NOT use with real money.**

### Reddit API Note

Reddit is changing developer access. The WSB signal generator is designed as a replaceable adapter. You may need to:
- Use Pushshift.io (free tier)
- Apply for Reddit API access
- Use a third-party data provider

### Pelosi Data Note

Congressional disclosure data is available from:
- https://disclosures.clerk.house.gov/

Be sure to respect usage restrictions and rate limits.

### LLM Classification (Optional)

For more accurate Cramer statement classification, enable LLM mode:
1. Set `OPENAI_API_KEY` in `.env`
2. Configure `classification_model` in `config.yaml`

## Control Principle

The LLM does **NOT** directly control order size or bypass the hard floor.

**LLM performs:**
- Language interpretation
- Sentiment classification
- Cramer statement classification
- WSB semantic analysis
- Signal explanation

**Deterministic Python performs:**
- Allocation
- Contract ranking
- Portfolio accounting
- Risk calculations
- $30,000 floor enforcement
- Order construction
- Execution validation

This keeps the intentionally irrational strategy from becoming unintentionally broken software.

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please open issues and pull requests.

## Disclaimer

This software is for educational and entertainment purposes only. It is not financial advice. The authors are not responsible for any losses incurred through use of this software.
