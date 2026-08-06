"""Mechanism-specific analysis contracts and algorithms."""

from datp_core.analysis.mechanisms.association import AssociationResult
from datp_core.analysis.mechanisms.clustering import ClusterStabilityResult
from datp_core.analysis.mechanisms.dispersion import GroupedDispersionResult
from datp_core.analysis.mechanisms.divergence import DivergenceResult
from datp_core.analysis.mechanisms.movement import ThresholdMovement
from datp_core.analysis.scientific_decision import ScientificDecisionResult

type MechanismEvidence = (
    AssociationResult
    | ClusterStabilityResult
    | DivergenceResult
    | GroupedDispersionResult
    | ScientificDecisionResult
    | ThresholdMovement
)
