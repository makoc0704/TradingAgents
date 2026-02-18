"""ResultReader — reads persisted results from the file system."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResultReader:
    """Reads analysis, backtest, and pipeline results from the results directory.

    Args:
        results_dir: Base directory for all results.
    """

    def __init__(self, results_dir: str = "./results"):
        self.results_dir = results_dir

    def list_tickers(self) -> List[str]:
        """List all tickers that have stored results."""
        if not os.path.isdir(self.results_dir):
            return []
        entries = []
        for name in os.listdir(self.results_dir):
            path = os.path.join(self.results_dir, name)
            if os.path.isdir(path) and name != "pipeline" and not name.startswith("."):
                entries.append(name)
        return sorted(entries)

    def list_dates_for_ticker(self, ticker: str) -> List[str]:
        """List available analysis dates for a ticker."""
        ticker_dir = os.path.join(self.results_dir, ticker)
        if not os.path.isdir(ticker_dir):
            return []
        dates = []
        for name in os.listdir(ticker_dir):
            if name.startswith("."):
                continue
            path = os.path.join(ticker_dir, name)
            if os.path.isdir(path):
                dates.append(name)
        return sorted(dates, reverse=True)

    def get_analysis_result(
        self, ticker: str, date: str
    ) -> Optional[Dict[str, Any]]:
        """Load a single analysis result (full state log).

        Reads from results/{ticker}/TradingAgentsStrategy_logs/full_states_log_{date}.json
        or falls back to results/{ticker}/{date}/ directory.
        """
        log_path = os.path.join(
            self.results_dir,
            ticker,
            "TradingAgentsStrategy_logs",
            f"full_states_log_{date}.json",
        )
        if os.path.isfile(log_path):
            return self._load_json(log_path)

        date_dir = os.path.join(self.results_dir, ticker, date)
        if not os.path.isdir(date_dir):
            return None

        result: Dict[str, Any] = {"ticker": ticker, "date": date}

        report_dir = os.path.join(date_dir, "reports")
        if os.path.isdir(report_dir):
            for fname in os.listdir(report_dir):
                if fname.endswith(".md"):
                    key = fname.replace(".md", "")
                    result[key] = self._load_text(
                        os.path.join(report_dir, fname)
                    )

        state_log_dir = os.path.join(date_dir, "TradingAgentsStrategy_logs")
        if os.path.isdir(state_log_dir):
            for fname in os.listdir(state_log_dir):
                if fname.endswith(".json"):
                    data = self._load_json(os.path.join(state_log_dir, fname))
                    if data:
                        result["state_log"] = data

        return result if len(result) > 2 else None

    def get_backtest_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Load a backtest result by ID (filename without extension)."""
        for candidate in [
            os.path.join(self.results_dir, f"{result_id}.json"),
            os.path.join(self.results_dir, "backtest", f"{result_id}.json"),
        ]:
            if os.path.isfile(candidate):
                return self._load_json(candidate)
        return None

    def get_portfolio_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Load a portfolio backtest result by ID."""
        for candidate in [
            os.path.join(self.results_dir, f"{result_id}.json"),
            os.path.join(self.results_dir, "portfolio", f"{result_id}.json"),
        ]:
            if os.path.isfile(candidate):
                return self._load_json(candidate)
        return None

    def list_pipeline_jobs(self) -> List[str]:
        """List all pipeline job names that have stored results."""
        pipeline_dir = os.path.join(self.results_dir, "pipeline")
        if not os.path.isdir(pipeline_dir):
            return []
        return sorted(
            name
            for name in os.listdir(pipeline_dir)
            if os.path.isdir(os.path.join(pipeline_dir, name))
        )

    def get_pipeline_history(
        self, job_name: str, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Load execution history for a pipeline job."""
        job_dir = os.path.join(self.results_dir, "pipeline", job_name)
        if not os.path.isdir(job_dir):
            return []

        files = [
            f
            for f in os.listdir(job_dir)
            if f.endswith(".json") and f != "latest.json"
        ]
        files.sort(reverse=True)

        results = []
        for fname in files[:limit]:
            data = self._load_json(os.path.join(job_dir, fname))
            if data:
                results.append(data)
        return results

    def get_pipeline_latest(
        self, job_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load the latest result for a pipeline job."""
        latest_path = os.path.join(
            self.results_dir, "pipeline", job_name, "latest.json"
        )
        return self._load_json(latest_path)

    def list_result_files(self) -> List[Dict[str, Any]]:
        """List all JSON result files in the results directory."""
        entries = []
        if not os.path.isdir(self.results_dir):
            return entries

        for fname in os.listdir(self.results_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(self.results_dir, fname)
                stat = os.stat(fpath)
                entries.append({
                    "filename": fname,
                    "path": fpath,
                    "size_bytes": stat.st_size,
                    "date": fname.replace(".json", ""),
                })
        return sorted(entries, key=lambda e: e["filename"], reverse=True)

    @staticmethod
    def _load_json(path: str) -> Optional[Dict[str, Any]]:
        """Load a JSON file, returning None on failure."""
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            logger.warning("Failed to load JSON from %s: %s", path, exc)
            return None

    @staticmethod
    def _load_text(path: str) -> str:
        """Load a text file, returning empty string on failure."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except IOError:
            return ""
