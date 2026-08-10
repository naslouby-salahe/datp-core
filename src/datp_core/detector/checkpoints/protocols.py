from datp_core.core.numeric import RelativeThresholdError, RoundNumber
from datp_core.detector.checkpoints.contracts import ConvergenceProtocol, DiagnosticSnapshotProtocol

DIAGNOSTIC_SNAPSHOT_PROTOCOL = DiagnosticSnapshotProtocol(
    diagnostic_rounds=tuple(RoundNumber(value) for value in (25, 50, 75, 100, 125, 150)),
    maximum_round=RoundNumber(200),
)
ANCHOR_DIAGNOSTIC_SNAPSHOT_PROTOCOL = DiagnosticSnapshotProtocol(
    diagnostic_rounds=(),
    maximum_round=RoundNumber(150),
    convergence=ConvergenceProtocol(
        rounds_initial=RoundNumber(40),
        relative_threshold=RelativeThresholdError(0.005),
        window=RoundNumber(10),
    ),
)
