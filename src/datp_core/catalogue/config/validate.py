"""Cross-document validation with stable, collectable issues."""

from __future__ import annotations

from collections.abc import Container

from ...kernel.errors import ValidationIssue, ValidationSeverity
from .bundle import AuthoredConfigBundle, AuthoredMapping, AuthoredValue


def _mapping(value: AuthoredValue) -> AuthoredMapping:
    return value if isinstance(value, dict) else {}


def _sequence(value: AuthoredValue | None) -> list[AuthoredValue]:
    return value if isinstance(value, list) else []


def _string_set(values: AuthoredMapping) -> set[str]:
    return set(values)


def validate_references(bundle: AuthoredConfigBundle) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    dataset_ids = {document.dataset for document in bundle.datasets}
    setup_ids = {document.dataset: _string_set(document.setups) for document in bundle.datasets}
    protocols = bundle.protocols
    collections: dict[str, set[str]] = {
        "metric_bundle": _string_set(protocols.metric_bundles),
        "training_profile": _string_set(protocols.training_profiles),
        "checkpoint_profile": _string_set(protocols.checkpoint_profiles),
        "seed_cohort": _string_set(protocols.seed_cohorts),
        "eligibility_policy": _string_set(protocols.eligibility_policies),
        "threshold_policy": _string_set(protocols.threshold_policies),
        "statistical_profile": _string_set(protocols.statistical_profiles),
        "result_type": _string_set(protocols.result_types),
        "report": _string_set(protocols.report_profiles),
        "metric": _string_set(protocols.metric_definitions),
    }
    populations = bundle.experiments.study_populations
    for population_id, raw_population in populations.items():
        population = _mapping(raw_population)
        dataset = population.get("dataset")
        setup = population.get("setup")
        if not isinstance(dataset, str) or dataset not in dataset_ids:
            issues.append(
                _issue("unknown_dataset", "experiments", ("study_populations", population_id, "dataset"), str(dataset))
            )
        elif not isinstance(setup, str) or setup not in setup_ids[dataset]:
            issues.append(
                _issue("unknown_setup", "experiments", ("study_populations", population_id, "setup"), str(setup))
            )
        _known(
            issues,
            collections["metric_bundle"],
            "metric_bundle",
            population.get("metric_bundle"),
            ("study_populations", population_id),
        )
    experiment_ids = {
        name for experiment in bundle.experiments.experiments if isinstance((name := experiment.get("name")), str)
    }
    for index, experiment in enumerate(bundle.experiments.experiments):
        location = ("experiments", index)
        for population in _sequence(experiment.get("populations")):
            _known(issues, populations, "population", population, location)
        for name in ("training_profile", "checkpoint_profile", "seed_cohort", "eligibility_policy"):
            _known(issues, collections[name], name, experiment.get(name), location)
        evaluation_labels: set[str] = set()
        for evaluation_index, raw_evaluation in enumerate(_sequence(experiment.get("evaluations"))):
            evaluation = _mapping(raw_evaluation)
            label = evaluation.get("label")
            if not isinstance(label, str) or label in evaluation_labels:
                issues.append(
                    _issue(
                        "duplicate_evaluation_label",
                        "experiments",
                        (*location, "evaluations", evaluation_index),
                        str(label),
                    )
                )
            if isinstance(label, str):
                evaluation_labels.add(label)
            _known(
                issues,
                collections["threshold_policy"],
                "threshold_policy",
                evaluation.get("threshold_policy"),
                (*location, "evaluations", evaluation_index),
            )
        analysis_labels: set[str] = set()
        for analysis_index, raw_analysis in enumerate(_sequence(experiment.get("analyses"))):
            analysis = _mapping(raw_analysis)
            label = analysis.get("label")
            if not isinstance(label, str) or label in analysis_labels:
                issues.append(
                    _issue(
                        "duplicate_analysis_label", "experiments", (*location, "analyses", analysis_index), str(label)
                    )
                )
            if isinstance(label, str):
                analysis_labels.add(label)
            _known(
                issues,
                collections["result_type"],
                "result_type",
                analysis.get("result_type"),
                (*location, "analyses", analysis_index),
            )
            _known(
                issues,
                collections["statistical_profile"],
                "statistical_profile",
                analysis.get("statistical_profile"),
                (*location, "analyses", analysis_index),
            )
        for report in _sequence(experiment.get("reports")):
            _known(issues, collections["report"], "report", report, location)
        for raw_prerequisite in _sequence(experiment.get("prerequisites")):
            prerequisite = _mapping(raw_prerequisite)
            _known(issues, experiment_ids, "experiment", prerequisite.get("experiment"), location)
    issues.extend(_acyclic_prerequisites(bundle))
    return tuple(issues)


def _known(
    issues: list[ValidationIssue],
    known: Container[str],
    name: str,
    value: AuthoredValue | None,
    path: tuple[str | int, ...],
) -> None:
    if not isinstance(value, str) or value not in known:
        issues.append(_issue(f"unknown_{name}", "experiments", path, str(value)))


def _issue(code: str, document: str, path: tuple[str | int, ...], value: str) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity=ValidationSeverity.ERROR,
        document=document,
        path=path,
        message=f"unknown or invalid reference: {value}",
    )


def _acyclic_prerequisites(bundle: AuthoredConfigBundle) -> tuple[ValidationIssue, ...]:
    graph: dict[str, tuple[str, ...]] = {}
    for experiment in bundle.experiments.experiments:
        name = experiment.get("name")
        if isinstance(name, str):
            graph[name] = tuple(
                reference
                for raw_prerequisite in _sequence(experiment.get("prerequisites"))
                if isinstance(
                    (reference := _mapping(raw_prerequisite).get("experiment")),
                    str,
                )
            )
    visiting: set[str] = set()
    visited: set[str] = set()
    issues: list[ValidationIssue] = []

    def visit(node: str) -> None:
        if node in visiting:
            issues.append(_issue("cyclic_prerequisite", "experiments", ("experiments", node), node))
            return
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, ()):
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for experiment_id in graph:
        visit(experiment_id)
    return tuple(issues)
