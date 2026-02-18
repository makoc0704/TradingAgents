import os

_PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))

DEFAULT_CONFIG = {
    "project_dir": _PROJECT_DIR,
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_dir": os.getenv("TRADINGAGENTS_DATA_DIR", os.path.join(_PROJECT_DIR, "data")),
    "data_cache_dir": os.path.join(_PROJECT_DIR, "dataflows/data_cache"),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "o4-mini",
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": "https://api.openai.com/v1",
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: yfinance, alpha_vantage, local
        "technical_indicators": "yfinance",  # Options: yfinance, alpha_vantage, local
        "fundamental_data": "alpha_vantage", # Options: openai, alpha_vantage, local
        "news_data": "alpha_vantage",        # Options: openai, alpha_vantage, google, local
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
        # Example: "get_news": "openai",               # Override category default
    },
    # Risk quantification settings
    "risk_lookback_days": 60,       # Days of historical data for risk calculations
    "risk_benchmark": "SPY",        # Benchmark ticker for beta calculation
    "risk_free_rate": 0.05,         # Annual risk-free rate (5%)
    "default_portfolio_value": 100000,  # Default portfolio value in USD
    "max_position_fraction": 0.25,  # Max fraction of portfolio for a single position
    # Backtesting settings
    "backtest_commission_rate": 0.001,     # Commission per trade (0.1%)
    "backtest_slippage_rate": 0.0005,      # Slippage per trade (0.05%)
    "backtest_trading_frequency": "daily", # "daily", "weekly", or "monthly"
    "backtest_profile": "standard",        # "full", "standard", or "quick"
    "backtest_reflection_mode": "periodic",# "none", "end_only", or "periodic"
    "backtest_reflection_interval": 20,    # Days between reflections
    "use_data_cache": True,                # Cache vendor API responses for backtests
    # Portfolio management settings
    "portfolio_weighting_strategy": "equal",     # "equal", "risk_parity", "min_variance", "signal_weighted"
    "portfolio_max_position_fraction": 0.30,     # Max weight per ticker
    "portfolio_min_position_fraction": 0.05,     # Min weight per ticker
    "portfolio_rebalance_threshold": 0.05,       # Drift that triggers rebalancing (5%)
    "portfolio_rebalance_frequency": "weekly",   # "daily", "weekly", or "monthly"
    # Pipeline settings
    "pipeline_config_path": "pipeline.yaml",         # Default pipeline config file
    "pipeline_results_dir": "./results/pipeline",    # Pipeline result storage
    # Web interface settings
    "web_host": "127.0.0.1",
    "web_port": 8000,
    "web_cors_origins": ["http://localhost:5173"],    # Vite dev server
}
