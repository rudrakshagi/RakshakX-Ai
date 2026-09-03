"""RakshakX Benchmark Protocol v2.0 -- evaluation framework."""

from rakshak.benchmark.adapters import (
    evaluate_live_scan,
    load_ground_truth,
    load_target_meta,
    vulnerabilities_to_predictions,
)
from rakshak.benchmark.metrics import (
    BenchmarkPrediction,
    BenchmarkScorecard,
    BenchmarkVerdict,
    EvaluationResult,
    build_scorecard,
    compute_f1,
    compute_precision,
    compute_recall,
    compute_verification_rate,
    evaluate_benchmark,
    evaluate_single,
)
from rakshak.benchmark.runner import (
    DockerEnvironment,
    HardwareEnvironment,
    LLMEnvironment,
    PythonEnvironment,
    RakshakEnvironmentFreeze,
    SecurityToolsEnvironment,
    SystemEnvironment,
    TargetEnvironment,
    freeze_environment,
)

__all__ = [
    "BenchmarkPrediction",
    "BenchmarkScorecard",
    "BenchmarkVerdict",
    "DockerEnvironment",
    "EvaluationResult",
    "HardwareEnvironment",
    "LLMEnvironment",
    "PythonEnvironment",
    "RakshakEnvironmentFreeze",
    "SecurityToolsEnvironment",
    "SystemEnvironment",
    "TargetEnvironment",
    "build_scorecard",
    "compute_f1",
    "compute_precision",
    "compute_recall",
    "compute_verification_rate",
    "evaluate_benchmark",
    "evaluate_live_scan",
    "evaluate_single",
    "freeze_environment",
    "load_ground_truth",
    "load_target_meta",
    "vulnerabilities_to_predictions",
]
