from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.domain.errors import ConfigurationError


class ConfigurationDocument(StrEnum):
    SCIENTIFIC_PROTOCOL = "scientific/protocol.yaml"
    SCIENTIFIC_DATASETS = "scientific/datasets.yaml"
    SCIENTIFIC_REGIMES = "scientific/regimes.yaml"
    SCIENTIFIC_MODELS = "scientific/models.yaml"
    SCIENTIFIC_THRESHOLDS = "scientific/thresholds.yaml"
    SCIENTIFIC_EVALUATION = "scientific/evaluation.yaml"
    SCIENTIFIC_EXPERIMENTS = "scientific/experiments.yaml"
    EXECUTION_PROFILES = "execution/profiles.yaml"
    ARTIFACT_POLICY = "artifacts/policy.yaml"
    REPORTING_POLICY = "reporting/policy.yaml"
    TEST_PROFILES = "tests/profiles.yaml"
    PROTOCOL_LOCK = "locks/protocol-lock.json"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfigurationDocumentPath:
    root: Path
    document: ConfigurationDocument

    def resolve(self) -> Path:
        root = self.root.resolve()
        path = (root / self.document.value).resolve()
        if root not in path.parents:
            raise ConfigurationError(
                detail="configuration document must resolve beneath the supplied configuration root",
                section="documents",
                field=self.document.value,
                mode="path_resolution",
            )
        return path


def configuration_document_path(*, root: Path, document: ConfigurationDocument) -> Path:
    return ConfigurationDocumentPath(root=root, document=document).resolve()
