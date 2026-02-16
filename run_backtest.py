"""First real backtest run — validates the full end-to-end pipeline.

Uses the "quick" profile (only Market Analyst, 1 debate round) over a
short period to minimize LLM costs while testing the full flow:
  Graph → Risk Metrics → Signal → Portfolio → Performance → Report
"""

from tradingagents import configure_logging
from tradingagents.backtesting import BacktestRunner, BacktestConfig, BacktestReport

configure_logging()

config = BacktestConfig(
    ticker="NVDA",
    start_date="2024-06-03",
    end_date="2024-06-07",        # Just 1 week (5 trading days)
    initial_capital=100_000,
    backtest_profile="quick",      # Only Market Analyst, 1 debate round
    reflection_mode="none",        # No reflection to save LLM costs
    use_data_cache=True,           # Cache API responses for repeatability
    config={
        "llm_provider": "openai",
        "quick_think_llm": "gpt-4o-mini",
        "deep_think_llm": "gpt-4o-mini",
        "backend_url": "https://api.openai.com/v1",
    },
)

print(f"Starting backtest: {config.ticker} from {config.start_date} to {config.end_date}")
print(f"Profile: {config.backtest_profile} | Reflection: {config.reflection_mode}")
print(f"Cache: {'enabled' if config.use_data_cache else 'disabled'}")
print()

result = BacktestRunner(config).run()
report = BacktestReport(result)

print()
print(report.to_summary())

# Save full result
report.save_json("backtest_result.json")
print("\nFull result saved to backtest_result.json")
