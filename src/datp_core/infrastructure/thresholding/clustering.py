from dataclasses import dataclass
from math import fsum, sqrt

import numpy as np
from blake3 import blake3
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from datp_core.application.ports.thresholding import B4ClusteringRequest, ClusteringStrategy
from datp_core.domain.errors import ThresholdError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import CalibrationScoreArtifactSet
from datp_core.domain.mathematics.quantiles import exact_quantile
from datp_core.domain.thresholding.clustering import (
    B4ClusteringAlgorithm,
    B4ClusteringSpec,
    B4Fingerprint,
    B4FingerprintField,
    B4FingerprintFitScope,
    B4FingerprintScalerSpec,
    ClusterAssignmentArtifact,
    ClusterAssignmentEntry,
    ClusterCentroidReference,
    ScaledB4Fingerprint,
    ScaledFingerprintReference,
)
from datp_core.domain.thresholding.policies import ThresholdPercentile
from datp_core.infrastructure.thresholding.quantiles import CalibrationScoreReader


@dataclass(frozen=True, slots=True, kw_only=True)
class ExactB4ClusteringStrategy(ClusteringStrategy):
    reader: CalibrationScoreReader

    def cluster(self, request: B4ClusteringRequest) -> ClusterAssignmentArtifact:
        self._verify_specification(request.clustering)
        client_ids, fingerprints = self._fingerprints(
            request.calibration_scores,
            request.eligible_clients.eligible_clients,
        )
        scaled = StandardScaler().fit_transform(np.asarray([fingerprint.values for fingerprint in fingerprints]))
        estimator = KMeans(
            n_clusters=request.clustering.cluster_count.value,
            init="k-means++",
            n_init=request.clustering.n_init.value,
            max_iter=request.clustering.max_iter.value,
            random_state=request.clustering.random_state.value,
        ).fit(scaled)
        canonical_labels, canonical_centers = _canonicalize_clusters(
            labels=estimator.labels_,
            centers=estimator.cluster_centers_,
        )
        scaled_fingerprints = tuple(
            ScaledFingerprintReference(client_id=client_id, fingerprint=_scaled_fingerprint(row))
            for client_id, row in zip(client_ids, scaled, strict=True)
        )
        assignments = tuple(
            ClusterAssignmentEntry(client_id=client_id, cluster_index=int(label))
            for client_id, label in zip(client_ids, canonical_labels, strict=True)
        )
        centroids = tuple(
            ClusterCentroidReference(cluster_index=index, fingerprint=_scaled_fingerprint(center))
            for index, center in enumerate(canonical_centers)
        )
        return ClusterAssignmentArtifact(
            clustering_identity=request.clustering.clustering_identity,
            assignments=assignments,
            scaled_fingerprints=scaled_fingerprints,
            centroid_references=centroids,
            content_hash=_assignment_hash(assignments=assignments, scaled=scaled_fingerprints, centroids=centroids),
        )

    def _verify_specification(self, specification: B4ClusteringSpec) -> None:
        expected_fields = (
            B4FingerprintField.MEAN,
            B4FingerprintField.STANDARD_DEVIATION,
            B4FingerprintField.SKEW,
            B4FingerprintField.P95,
        )
        if not all(
            (
                specification.is_canonical_k,
                specification.fingerprint_fields == expected_fields,
                specification.scaler is B4FingerprintScalerSpec.STANDARD_SCALER,
                specification.scaler_fit_scope is B4FingerprintFitScope.ELIGIBLE_CLIENT_FINGERPRINTS,
                specification.algorithm is B4ClusteringAlgorithm.KMEANS_PLUS_PLUS,
                specification.n_init.value == 10,
                specification.max_iter.value == 300,
                specification.scikit_learn_version.value == "1.9.0",
            )
        ):
            raise ThresholdError(
                detail="B4 clustering requires the complete locked canonical specification",
                policy="b4",
                missing_field="canonical B4 specification",
            )

    def _fingerprints(
        self,
        calibration_scores: CalibrationScoreArtifactSet,
        eligible_clients: tuple[ClientId, ...],
    ) -> tuple[tuple[ClientId, ...], tuple[B4Fingerprint, ...]]:
        selected = _eligible_client_indexes(
            calibration_scores=calibration_scores,
            eligible_clients=eligible_clients,
        )
        if len(selected) < 3:
            raise ThresholdError(
                detail="B4 clustering needs at least three eligible client fingerprints",
                policy="b4",
                missing_field="eligible client fingerprints",
            )
        return (
            tuple(client_id for client_id, _ in selected),
            tuple(
                _fingerprint(self.reader.read(calibration_scores=calibration_scores, client_index=index))
                for _, index in selected
            ),
        )


def _eligible_client_indexes(
    *, calibration_scores: CalibrationScoreArtifactSet, eligible_clients: tuple[ClientId, ...]
) -> tuple[tuple[ClientId, int], ...]:
    return tuple(
        (entry.client_id, index)
        for index, entry in enumerate(calibration_scores.per_client.values.entries)
        if entry.client_id in eligible_clients
    )


def _fingerprint(scores: tuple[float, ...]) -> B4Fingerprint:
    values = np.asarray(scores, dtype=np.float64)
    if values.size == 0 or not np.isfinite(values).all():
        raise ThresholdError(
            detail="B4 fingerprint requires non-empty finite calibration scores",
            policy="b4",
            missing_field="finite calibration scores",
        )
    return B4Fingerprint(
        mean=float(np.mean(values)),
        standard_deviation=float(np.std(values)),
        skew=_unbiased_skew(tuple(float(value) for value in values)),
        p95=exact_quantile(values=tuple(float(value) for value in values), percentile=ThresholdPercentile(value=0.95)),
    )


def _unbiased_skew(values: tuple[float, ...]) -> float:
    if len(values) < 3:
        return 0.0
    mean = fsum(values) / len(values)
    second_moment = fsum((value - mean) ** 2 for value in values) / len(values)
    if second_moment == 0:
        return 0.0
    third_moment = fsum((value - mean) ** 3 for value in values) / len(values)
    correction = sqrt(len(values) * (len(values) - 1)) / (len(values) - 2)
    return correction * third_moment / second_moment**1.5


def _canonicalize_clusters(*, labels: np.ndarray, centers: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ordering = tuple(sorted(range(len(centers)), key=lambda index: tuple(float(value) for value in centers[index])))
    canonical_index = {original: canonical for canonical, original in enumerate(ordering)}
    return np.asarray([canonical_index[int(label)] for label in labels]), centers[list(ordering)]


def _scaled_fingerprint(values: np.ndarray) -> ScaledB4Fingerprint:
    return ScaledB4Fingerprint(
        mean=float(values[0]),
        standard_deviation=float(values[1]),
        skew=float(values[2]),
        p95=float(values[3]),
    )


def _assignment_hash(
    *,
    assignments: tuple[ClusterAssignmentEntry, ...],
    scaled: tuple[ScaledFingerprintReference, ...],
    centroids: tuple[ClusterCentroidReference, ...],
) -> str:
    values = (
        *(f"a:{entry.client_id.value}:{entry.cluster_index}" for entry in assignments),
        *(f"s:{entry.client_id.value}:{entry.fingerprint.values!r}" for entry in scaled),
        *(f"c:{entry.cluster_index}:{entry.fingerprint.values!r}" for entry in centroids),
    )
    return blake3("|".join(values).encode()).hexdigest()
