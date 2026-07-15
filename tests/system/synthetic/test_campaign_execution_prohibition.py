from datp_core.composition.root import (
    PHASE_ONE_COMMAND_USE_CASE,
    CompositionCommand,
    CompositionCommandFailure,
    RunCompositionCommandRequest,
)
from datp_core.domain.errors import ConfigurationError


def test_phase_one_boundary_refuses_to_construct_an_executable_campaign_without_typed_bindings() -> None:
    result = PHASE_ONE_COMMAND_USE_CASE.execute_command(RunCompositionCommandRequest(command=CompositionCommand.RUN))

    assert isinstance(result, CompositionCommandFailure)
    assert type(result.error) is ConfigurationError
    assert result.error.field == "ports"
    assert result.error.mode == "run"
