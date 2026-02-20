"""JobRunner — executes a single pipeline job with retry logic."""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from tradingagents.default_config import DEFAULT_CONFIG

from .models import JobConfig, JobResult
from .notifier import Notifier
from .result_store import ResultStore

logger = logging.getLogger(__name__)


class JobRunner:
    """Executes individual pipeline jobs by delegating to existing runners.

    Each ``execute()`` call is fully self-contained.  On failure the runner
    retries with exponential backoff up to ``max_retries``.

    Args:
        result_store: Where to persist job results.
        notifier: Notification dispatcher.
    """

    def __init__(self, result_store: ResultStore, notifier: Notifier):
        self.result_store = result_store
        self.notifier = notifier

    def execute(self, job_config: JobConfig) -> JobResult:
        """Run a job, with retries on failure.

        Args:
            job_config: Configuration for the job to execute.

        Returns:
            JobResult describing the outcome.
        """
        max_retries = job_config.schedule.max_retries
        retry_delay = job_config.schedule.retry_delay_seconds
        last_error: Optional[str] = None

        for attempt in range(1, max_retries + 1):
            logger.info(
                "Executing job '%s' (attempt %d/%d, type=%s)",
                job_config.name, attempt, max_retries, job_config.job_type,
            )
            started = datetime.now()

            try:
                result = self._run_job(job_config, started)

                # Save and notify
                result.result_path = self.result_store.save(result)
                signal_changed = False
                if result.signal:
                    signal_changed = self.result_store.has_signal_changed(
                        job_config.name, result.signal,
                    )
                self.notifier.notify(
                    result,
                    config=job_config.notification,
                    signal_changed=signal_changed,
                )
                return result

            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.error(
                    "Job '%s' attempt %d failed: %s",
                    job_config.name, attempt, last_error,
                )

                if attempt < max_retries:
                    delay = retry_delay * (2 ** (attempt - 1))
                    logger.info(
                        "Retrying '%s' in %ds...",
                        job_config.name, delay,
                    )
                    time.sleep(delay)

        # All retries exhausted
        finished = datetime.now()
        failure_result = JobResult(
            job_name=job_config.name,
            job_type=job_config.job_type,
            started_at=started,
            finished_at=finished,
            status="failure",
            duration_seconds=(finished - started).total_seconds(),
            error=last_error,
        )
        failure_result.result_path = self.result_store.save(failure_result)
        self.notifier.notify(
            failure_result,
            config=job_config.notification,
            signal_changed=False,
        )
        return failure_result

    def _run_job(self, job_config: JobConfig, started: datetime) -> JobResult:
        """Dispatch to the appropriate runner based on ``job_type``.

        Raises:
            ValueError: If ``job_type`` is unknown.
            Exception: Any exception from the underlying runner.
        """
        job_type = job_config.job_type

        if job_type == "single_analysis":
            return self._run_single_analysis(job_config, started)
        elif job_type == "backtest":
            return self._run_backtest(job_config, started)
        elif job_type == "portfolio":
            return self._run_portfolio(job_config, started)
        elif job_type == "live_trading":
            return self._run_live_trading(job_config, started)
        else:
            raise ValueError(f"Unknown job_type: '{job_type}'")

    def _resolve_date(self, analysis_date: str) -> str:
        """Convert special date tokens to actual date strings."""
        today = datetime.now()
        if analysis_date == "today":
            return today.strftime("%Y-%m-%d")
        elif analysis_date == "yesterday":
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        return analysis_date

    def _build_config(self, job_config: JobConfig) -> dict:
        """Build effective config by merging job config with defaults."""
        config = DEFAULT_CONFIG.copy()
        config.update(job_config.config)
        return config

    def _run_single_analysis(
        self, job_config: JobConfig, started: datetime,
    ) -> JobResult:
        """Run a single-ticker analysis via TradingAgentsGraph.propagate()."""
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        effective_config = self._build_config(job_config)
        date_str = self._resolve_date(job_config.analysis_date)
        ticker = job_config.tickers[0]

        graph = TradingAgentsGraph(
            selected_analysts=effective_config.get(
                "selected_analysts", ["market", "fundamentals"]
            ),
            debug=False,
            config=effective_config,
        )

        state, signal = graph.propagate(ticker, date_str)

        signal_str = str(signal) if signal else "HOLD"
        if hasattr(signal, "action"):
            signal_str = signal.action.upper()

        finished = datetime.now()
        return JobResult(
            job_name=job_config.name,
            job_type=job_config.job_type,
            started_at=started,
            finished_at=finished,
            status="success",
            duration_seconds=(finished - started).total_seconds(),
            signal=signal_str,
        )

    def _run_backtest(
        self, job_config: JobConfig, started: datetime,
    ) -> JobResult:
        """Run a backtest via BacktestRunner."""
        from tradingagents.backtesting import BacktestRunner, BacktestConfig

        effective_config = self._build_config(job_config)
        date_str = self._resolve_date(job_config.analysis_date)

        bt_config = BacktestConfig(
            ticker=job_config.tickers[0],
            start_date=effective_config.get("backtest_start_date", date_str),
            end_date=effective_config.get("backtest_end_date", date_str),
            initial_capital=effective_config.get("default_portfolio_value", 100_000),
            backtest_profile=effective_config.get("backtest_profile", "quick"),
            reflection_mode=effective_config.get("backtest_reflection_mode", "none"),
            use_data_cache=effective_config.get("use_data_cache", True),
            config=effective_config,
        )

        result = BacktestRunner(bt_config).run()

        finished = datetime.now()
        return JobResult(
            job_name=job_config.name,
            job_type=job_config.job_type,
            started_at=started,
            finished_at=finished,
            status="success",
            duration_seconds=(finished - started).total_seconds(),
            performance=result.performance,
        )

    def _run_portfolio(
        self, job_config: JobConfig, started: datetime,
    ) -> JobResult:
        """Run a portfolio backtest via PortfolioManager."""
        from tradingagents.portfolio import PortfolioManager, PortfolioConfig

        effective_config = self._build_config(job_config)
        date_str = self._resolve_date(job_config.analysis_date)

        pf_config = PortfolioConfig(
            tickers=job_config.tickers,
            start_date=effective_config.get("portfolio_start_date", date_str),
            end_date=effective_config.get("portfolio_end_date", date_str),
            initial_capital=effective_config.get("default_portfolio_value", 100_000),
            weighting_strategy=effective_config.get(
                "portfolio_weighting_strategy", "equal"
            ),
            max_position_fraction=effective_config.get(
                "portfolio_max_position_fraction", 0.30
            ),
            min_position_fraction=effective_config.get(
                "portfolio_min_position_fraction", 0.05
            ),
            rebalance_threshold=effective_config.get(
                "portfolio_rebalance_threshold", 0.05
            ),
            rebalance_frequency=effective_config.get(
                "portfolio_rebalance_frequency", "weekly"
            ),
            backtest_profile=effective_config.get("backtest_profile", "quick"),
            reflection_mode=effective_config.get("backtest_reflection_mode", "none"),
            use_data_cache=effective_config.get("use_data_cache", True),
            config=effective_config,
        )

        result = PortfolioManager(pf_config).run()

        # Extract signal summary from per-ticker signals
        signal_summary = None
        if result.snapshots:
            last_snap = result.snapshots[-1]
            actions = last_snap.actions
            if actions:
                signal_summary = ", ".join(
                    f"{t}={a}" for t, a in actions.items()
                )

        finished = datetime.now()
        return JobResult(
            job_name=job_config.name,
            job_type=job_config.job_type,
            started_at=started,
            finished_at=finished,
            status="success",
            duration_seconds=(finished - started).total_seconds(),
            signal=signal_summary,
            performance=result.performance,
        )

    def _run_live_trading(
        self, job_config: JobConfig, started: datetime,
    ) -> JobResult:
        """Run live trading via LiveRunner."""
        from tradingagents.live import LiveRunner, LiveConfig

        effective_config = self._build_config(job_config)

        live_config = LiveConfig(
            tickers=job_config.tickers,
            mode=effective_config.get("live_mode", "paper"),
            broker_type=effective_config.get("live_broker_type", "dummy"),
            state_path=effective_config.get("live_state_path", "results/live/state.json"),
            initial_capital=effective_config.get("live_initial_capital", 200.0),
            commission_rate=effective_config.get("live_commission_rate", 0.001),
            slippage_rate=effective_config.get("live_slippage_rate", 0.0005),
            selected_analysts=effective_config.get(
                "selected_analysts", ["market", "fundamentals"]
            ),
            backtest_profile=effective_config.get("backtest_profile", "standard"),
            config=effective_config,
        )

        result = LiveRunner(live_config).run()

        # Extract signal summary
        signal_summary = ", ".join(
            f"{ticker}={signal.action}"
            for ticker, signal in result.signals.items()
        )

        finished = datetime.now()
        return JobResult(
            job_name=job_config.name,
            job_type=job_config.job_type,
            started_at=started,
            finished_at=finished,
            status="success",
            duration_seconds=(finished - started).total_seconds(),
            signal=signal_summary,
            performance=result.performance_metrics,
        )
