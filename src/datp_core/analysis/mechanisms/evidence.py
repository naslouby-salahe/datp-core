"""Closed union of mechanism-evidence result contracts."""

from datp_core.analysis.decisions import ScientificDecisionResult
from datp_core.analysis.mechanisms.association import AssociationResult
from datp_core.analysis.mechanisms.clustering import ClusterStabilityResult
from datp_core.analysis.mechanisms.dispersion import GroupedDispersionResult
from datp_core.analysis.mechanisms.divergence import DivergenceResult
from datp_core.analysis.mechanisms.movement import ThresholdMovement

type MechanismEvidence = (
    AssociationResult
    | ClusterStabilityResult
    | DivergenceResult
    | GroupedDispersionResult
    | ScientificDecisionResult
    | ThresholdMovement
)
