"""First portfolio backtest — validates the multi-asset pipeline.

Uses 3 tickers over 3 trading days with the "quick" profile to
minimize LLM costs while testing the full portfolio flow:
  Graph (per ticker) -> Optimizer -> Rebalancer -> MultiAssetPortfolio -> Performance
"""

import json
from tradingagents import configure_logging
from tradingagents.portfolio import PortfolioManager, PortfolioConfig

configure_logging()

config = PortfolioConfig(
    tickers=["NVDA", "AAPL", "MSFT"],
    start_date="2024-06-03",
    end_date="2024-06-05",           # 3 trading days
    initial_capital=100_000,
    weighting_strategy="equal",       # 1/3 per ticker
    max_position_fraction=0.40,
    min_position_fraction=0.05,
    rebalance_threshold=0.10,
    rebalance_frequency="daily",
    trading_frequency="daily",
    backtest_profile="quick",         # Only Market Analyst, 1 debate round
    reflection_mode="none",           # No reflection to save LLM costs
    use_data_cache=True,              # Cache API responses
    commission_rate=0.001,
    slippage_rate=0.0005,
    config={
        "llm_provider": "openai",
        "quick_think_llm": "gpt-4o-mini",
        "deep_think_llm": "gpt-4o-mini",
        "backend_url": "https://api.openai.com/v1",
    },
)

print("=" * 60)
print("  PORTFOLIO BACKTEST")
print("=" * 60)
print(f"  Tickers:    {', '.join(config.tickers)}")
print(f"  Period:     {config.start_date} to {config.end_date}")
print(f"  Capital:    ${config.initial_capital:,.0f}")
print(f"  Strategy:   {config.weighting_strategy}")
print(f"  Profile:    {config.backtest_profile}")
print(f"  Cache:      {'enabled' if config.use_data_cache else 'disabled'}")
print("=" * 60)
print()

result = PortfolioManager(config).run()

# Print summary
print()
print("=" * 60)
print("  PORTFOLIO RESULT SUMMARY")
print("=" * 60)
perf = result.performance
print(f"  Trading Days:    {result.total_trading_days}")
print(f"  Total Trades:    {result.total_trades}")
print()

if perf:
    print("--- Performance ---")
    print(f"  Final Value:     ${perf.get('final_value', 0):,.2f}")
    print(f"  Total Return:    {perf.get('total_return', 0) * 100:+.2f}%")
    print(f"  Annual Return:   {perf.get('annual_return', 0) * 100:+.2f}%")
    print(f"  Max Drawdown:    {perf.get('max_drawdown', 0) * 100:.2f}%")
    print(f"  Sharpe Ratio:    {perf.get('sharpe_ratio', 0):.2f}")
    print(f"  Total Commission:${perf.get('total_commission', 0):,.2f}")
    print()

print("--- Per Ticker ---")
for ticker, tp in result.per_ticker_performance.items():
    print(f"  {ticker}: {tp.get('total_trades', 0)} trades, "
          f"B&H: {tp.get('buy_and_hold_return', 0) * 100:+.2f}%, "
          f"Commission: ${tp.get('total_commission', 0):,.2f}")

if result.snapshots:
    print()
    print("--- Daily Snapshots ---")
    for snap in result.snapshots:
        pos_str = ", ".join(
            f"{t}={p.shares}sh" for t, p in snap.positions.items()
        )
        act_str = ", ".join(
            f"{t}={a}" for t, a in snap.actions.items()
        )
        print(f"  {snap.date}: ${snap.total_value:,.2f} "
              f"(return: {snap.daily_return * 100:+.2f}%) "
              f"| {act_str} | Positions: {pos_str or 'none'}")

print()
print("=" * 60)

# Save full result
output_file = "portfolio_backtest_result.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result.to_dict(), f, indent=2, default=str)
print(f"Full result saved to {output_file}")
