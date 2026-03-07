"""
AWS CDK Stack: Vision Factory CloudWatch Dashboard — Practical Edition
=======================================================================

Philosophy: Simple, real, actionable.
  - Number counters for quick health check
  - Log query widget to see what actually happened in the last job
  - One trend graph (success vs failure)
  - Alarm panel with clear OK / ALARM labels

Custom metrics published by lambda_function.py (VisionFactory/Pipeline namespace):
  PDFInputs            — emitted once per invocation (= every job triggered)
  SuccessfulJSONOutputs — emitted when pipeline fully succeeds (JSON written)
  PipelineErrors        — emitted on any _InputError, _PipelineError, or Exception
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cw,
    aws_logs as logs,
)
from constructs import Construct


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lambda_metric(
    metric_name: str,
    function_name: str,
    *,
    statistic: str = "Sum",
    period: Duration = Duration.hours(24),
    label: str | None = None,
    color: str | None = None,
) -> cw.Metric:
    kwargs: dict = dict(
        namespace="AWS/Lambda",
        metric_name=metric_name,
        dimensions_map={"FunctionName": function_name},
        statistic=statistic,
        period=period,
    )
    if label:
        kwargs["label"] = label
    if color:
        kwargs["color"] = color
    return cw.Metric(**kwargs)


def _custom_metric(
    metric_name: str,
    *,
    statistic: str = "Sum",
    period: Duration = Duration.hours(24),
    label: str | None = None,
    color: str | None = None,
) -> cw.Metric:
    kwargs: dict = dict(
        namespace="VisionFactory/Pipeline",
        metric_name=metric_name,
        statistic=statistic,
        period=period,
    )
    if label:
        kwargs["label"] = label
    if color:
        kwargs["color"] = color
    return cw.Metric(**kwargs)


# ---------------------------------------------------------------------------
# Stack
# ---------------------------------------------------------------------------

class VisionFactoryDashboardStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_function_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        fn = lambda_function_name
        log_group_name = f"/aws/lambda/{fn}"

        # ── Custom Metrics (24h window — "today at a glance") ───────────────

        total_jobs = _custom_metric(
            "PDFInputs",
            label="Total Jobs",
            color="#1f77b4",   # blue
        )

        succeeded = _custom_metric(
            "SuccessfulJSONOutputs",
            label="Succeeded",
            color="#2ca02c",   # green
        )

        pipeline_errors = _custom_metric(
            "PipelineErrors",
            label="Pipeline Errors",
            color="#d62728",   # red
        )

        # ── AWS/Lambda Built-in Metrics (24h) ───────────────────────────────

        lambda_errors = _lambda_metric(
            "Errors", fn,
            label="Lambda Crashes",
            color="#9467bd",   # purple
        )

        throttles = _lambda_metric(
            "Throttles", fn,
            label="Throttles",
            color="#ff7f0e",   # orange
        )

        duration_p95 = _lambda_metric(
            "Duration", fn,
            statistic="p95",
            period=Duration.minutes(5),   # finer grain for trend graph
            label="p95 Duration (ms)",
            color="#ff7f0e",
        )

        # ── Alarms ──────────────────────────────────────────────────────────

        # Alarm 1: any pipeline errors in the last 5 min
        pipeline_error_alarm = cw.Alarm(
            self,
            "PipelineErrorAlarm",
            alarm_name=f"{fn}-PipelineErrors",
            alarm_description=(
                "One or more PDF processing jobs failed in the last 5 minutes. "
                "Check the LOG ERRORS widget below for the stack trace."
            ),
            metric=_custom_metric(
                "PipelineErrors",
                period=Duration.minutes(5),
                label="Pipeline Errors (5m)",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        # Alarm 2: AWS-level Lambda crash (unhandled exception)
        lambda_error_alarm = cw.Alarm(
            self,
            "LambdaErrorAlarm",
            alarm_name=f"{fn}-LambdaCrashes",
            alarm_description=(
                "Lambda itself crashed (unhandled exception). "
                "This is worse than a pipeline error — check for memory/timeout issues."
            ),
            metric=_lambda_metric(
                "Errors", fn,
                period=Duration.minutes(5),
                label="Lambda Errors (5m)",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        # Alarm 3: duration > 4 minutes (Lambda max is 15 min; flag at 4m as early warning)
        duration_alarm = cw.Alarm(
            self,
            "LambdaDurationAlarm",
            alarm_name=f"{fn}-SlowProcessing",
            alarm_description=(
                "PDF processing is taking over 4 minutes (p95). "
                "May indicate large PDFs, slow AI responses, or network latency."
            ),
            metric=_lambda_metric(
                "Duration", fn,
                statistic="p95",
                period=Duration.minutes(5),
                label="Duration p95 (5m)",
            ),
            threshold=240_000,   # 4 minutes in ms
            evaluation_periods=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        # ── Dashboard ────────────────────────────────────────────────────────

        dashboard = cw.Dashboard(
            self,
            "VisionFactoryDashboard",
            dashboard_name="VisionFactory-PDF-Pipeline",
        )

        # ════════════════════════════════════════════════════════════════════
        # ROW 1 — Header
        # ════════════════════════════════════════════════════════════════════

        dashboard.add_widgets(
            cw.TextWidget(
                markdown=(
                    "# Vision Factory — PDF → JSON Pipeline\n"
                    f"**Function:** `{fn}`  |  "
                    "**All counters show last 24 hours.**  "
                    "Scroll down for live error logs from the last run."
                ),
                width=24,
                height=2,
            )
        )

        # ════════════════════════════════════════════════════════════════════
        # ROW 2 — Five number counters (most important, left to right)
        # ════════════════════════════════════════════════════════════════════

        dashboard.add_widgets(
            # 1. Total jobs triggered today
            cw.SingleValueWidget(
                title="📄 Total Jobs (24h)",
                metrics=[total_jobs],
                width=4,
                height=4,
            ),
            # 2. How many succeeded
            cw.SingleValueWidget(
                title="✅ Succeeded (24h)",
                metrics=[succeeded],
                width=4,
                height=4,
            ),
            # 3. How many had pipeline errors (your custom error tracking)
            cw.SingleValueWidget(
                title="❌ Pipeline Errors (24h)",
                metrics=[pipeline_errors],
                width=4,
                height=4,
            ),
            # 4. AWS-level Lambda crashes (unhandled exceptions, timeouts, OOM)
            cw.SingleValueWidget(
                title="💥 Lambda Crashes (24h)",
                metrics=[lambda_errors],
                width=4,
                height=4,
            ),
            # 5. Throttles — Lambda being rate-limited
            cw.SingleValueWidget(
                title="⏸️ Throttled Invocations (24h)",
                metrics=[throttles],
                width=4,
                height=4,
            ),
        )

        # ════════════════════════════════════════════════════════════════════
        # ROW 3 — What to read / what it means
        # ════════════════════════════════════════════════════════════════════

        dashboard.add_widgets(
            cw.TextWidget(
                markdown=(
                    "## What each number means\n"
                    "| Counter | Target | What to do if wrong |\n"
                    "|---|---|---|\n"
                    "| 📄 Total Jobs | Should rise as PDFs are submitted | Low = nothing is triggering the pipeline (check your API caller or S3 event) |\n"
                    "| ✅ Succeeded | Should equal Total Jobs | Gap = pipeline errors. Check **LOG ERRORS** section below |\n"
                    "| ❌ Pipeline Errors | Should be **zero** | Any value = check log errors. Usually bad PDF, API failure, or parsing issue |\n"
                    "| 💥 Lambda Crashes | Should be **zero** | Means Lambda OOM, timeout, or import error — check Lambda config |\n"
                    "| ⏸️ Throttled | Should be **zero** | Means concurrent limit hit — raise Lambda reserved concurrency |\n"
                ),
                width=24,
                height=5,
            )
        )

        # ════════════════════════════════════════════════════════════════════
        # ROW 4 — Alarm panel + Duration metric
        # ════════════════════════════════════════════════════════════════════

        dashboard.add_widgets(
            cw.AlarmStatusWidget(
                title="🚨 Active Alarms — Current Status",
                alarms=[pipeline_error_alarm, lambda_error_alarm, duration_alarm],
                width=8,
                height=6,
            ),
            cw.GraphWidget(
                title="⏱ Processing Time — p95 (last 3h)",
                left=[duration_p95],
                left_y_axis=cw.YAxisProps(min=0, label="ms"),
                width=16,
                height=6,
                left_annotations=[
                    cw.HorizontalAnnotation(
                        value=240_000,
                        label="4 min warning",
                        color="#ff7f0e",
                    )
                ],
                period=Duration.hours(3),
            ),
        )

        # ════════════════════════════════════════════════════════════════════
        # ROW 5 — Success vs Failure trend (5-min buckets, last 12h)
        # ════════════════════════════════════════════════════════════════════

        dashboard.add_widgets(
            cw.GraphWidget(
                title="✅ Successes vs ❌ Pipeline Errors (12h trend)",
                left=[
                    _custom_metric(
                        "SuccessfulJSONOutputs",
                        period=Duration.minutes(5),
                        label="Successes",
                        color="#2ca02c",
                    ),
                    _custom_metric(
                        "PipelineErrors",
                        period=Duration.minutes(5),
                        label="Pipeline Errors",
                        color="#d62728",
                    ),
                ],
                left_y_axis=cw.YAxisProps(min=0, label="Count"),
                width=24,
                height=6,
                period=Duration.hours(12),
            )
        )

        # ════════════════════════════════════════════════════════════════════
        # ROW 6 — Live Log Insights: ERRORS from the last run
        # ════════════════════════════════════════════════════════════════════

        dashboard.add_widgets(
            cw.TextWidget(
                markdown=(
                    "## 🔍 Live Error Logs — Most Recent Errors\n"
                    "The table below shows the last **20 ERROR and WARNING lines** from CloudWatch Logs.  \n"
                    "Use this to diagnose a specific failed job. Each line is timestamped.  \n"
                    "> **Tip:** If you see `PipelineErrors=1` above but no entries here, the error was a Lambda crash — check Lambda Crashes counter."
                ),
                width=24,
                height=3,
            )
        )

        # Log Insights widget — shows ERROR/WARNING log lines from real executions
        dashboard.add_widgets(
            cw.LogQueryWidget(
                title="Last 20 ERROR / WARNING log lines",
                log_group_names=[log_group_name],
                query_lines=[
                    "fields @timestamp, @message",
                    "filter @message like /ERROR|WARNING|error|exception|Exception|failed|Failed/",
                    "sort @timestamp desc",
                    "limit 20",
                ],
                width=24,
                height=8,
            )
        )

        # ════════════════════════════════════════════════════════════════════
        # ROW 7 — Recent successful runs (to confirm things work)
        # ════════════════════════════════════════════════════════════════════

        dashboard.add_widgets(
            cw.TextWidget(
                markdown=(
                    "## ✅ Recent Successful Completions\n"
                    "Lines below confirm successful pipeline runs.  \n"
                    "> **What to look for:** Each line has the filename and how many pages were processed."
                ),
                width=24,
                height=2,
            )
        )

        dashboard.add_widgets(
            cw.LogQueryWidget(
                title="Last 10 successful completions",
                log_group_names=[log_group_name],
                query_lines=[
                    "fields @timestamp, @message",
                    "filter @message like /SuccessfulJSONOutputs|Webhook delivered|Pipeline completed|statusCode.*200/",
                    "sort @timestamp desc",
                    "limit 10",
                ],
                width=24,
                height=6,
            )
        )
