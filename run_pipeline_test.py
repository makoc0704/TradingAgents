"""Pipeline validation — runs a single analysis job via PipelineManager.

Tests the full pipeline flow:
  YAML Config -> JobRunner -> TradingAgentsGraph.propagate() -> ResultStore -> Notifier
"""

from tradingagents import configure_logging
from tradingagents.pipeline import PipelineManager

configure_logging()

print("=" * 60)
print("  PIPELINE VALIDATION TEST")
print("=" * 60)
print("  Config:  pipeline_test.yaml")
print("  Job:     test_nvda_analysis (single_analysis)")
print("  Ticker:  NVDA on 2024-06-05")
print("  Profile: quick (Market Analyst only)")
print("=" * 60)
print()

manager = PipelineManager("pipeline_test.yaml")

# Show pipeline status before run
status = manager.status()
print(f"Pipeline: {status['total_jobs']} jobs ({status['enabled_jobs']} enabled)")
for job in status["jobs"]:
    print(f"  - {job['name']} [{job['job_type']}] "
          f"cron={job['cron']} enabled={job['enabled']}")
print()

# Run the job immediately (no scheduler needed)
print("Running job 'test_nvda_analysis' now...")
print()
manager.run_job("test_nvda_analysis")

# Show status after run
print()
print("=" * 60)
print("  POST-RUN STATUS")
print("=" * 60)
status = manager.status()
for job in status["jobs"]:
    print(f"  Job:        {job['name']}")
    print(f"  Last Run:   {job.get('last_run', 'N/A')}")
    print(f"  Status:     {job.get('last_status', 'N/A')}")
    print(f"  Signal:     {job.get('last_signal', 'N/A')}")
    print(f"  Duration:   {job.get('last_duration', 'N/A')}s")
print("=" * 60)
