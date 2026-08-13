from tests.unit.analysis.test_equity_utility import _document

from datp_core.analysis.mechanisms.equity_utility import confirmatory_equity_utility_bundle
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.presentation.export import _mechanism_tables


def test_confirmatory_equity_utility_publication_retains_one_cell_per_measure() -> None:
    bundle = confirmatory_equity_utility_bundle(
        (
            (
                _document(seed=1, method=FederatedThresholdMethod.SHARED_THRESHOLD, offset=1.0),
                _document(seed=1, method=FederatedThresholdMethod.LOCAL_THRESHOLD, offset=0.0),
            ),
            (
                _document(seed=2, method=FederatedThresholdMethod.SHARED_THRESHOLD, offset=3.0),
                _document(seed=2, method=FederatedThresholdMethod.LOCAL_THRESHOLD, offset=1.0),
            ),
        )
    )

    tables = _mechanism_tables((bundle,))

    table = next(table for table in tables if table.title == "Confirmatory equity–utility companion table")
    assert len(table.cells) == len(bundle.measures)
    assert len({cell.metric for cell in table.cells}) == len(bundle.measures)
