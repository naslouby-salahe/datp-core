"""Shared scalar semantics for labels, hashes, splits, and encoded names."""

from __future__ import annotations

import hashlib
import struct

from datp_core.data.contracts.enums import (
    EncodedFeatureNaming,
    HashAlgorithm,
    LabelCasePolicy,
    SplitMembership,
)
from datp_core.data.contracts.materialization import HashConfig, RandomRatios


def normalize_label(value: str, policy: LabelCasePolicy) -> str:
    normalized = value.strip()
    if policy is LabelCasePolicy.EXACT:
        return normalized
    if policy is LabelCasePolicy.CASEFOLD:
        return normalized.casefold()
    if policy is LabelCasePolicy.UPPER:
        return normalized.upper()
    return normalized.lower()


def row_digest(
    numeric_values: tuple[float, ...],
    text_values: tuple[str | None, ...],
    boolean_values: tuple[bool, ...],
    config: HashConfig,
) -> bytes:
    payload = bytearray()
    payload.extend(struct.pack(f"!{len(numeric_values)}d", *numeric_values))
    for value in text_values:
        encoded = b"" if value is None else value.encode("utf-8")
        payload.extend(len(encoded).to_bytes(4, byteorder="big", signed=False))
        payload.extend(encoded)
    payload.extend(bytes(int(value) for value in boolean_values))
    if config.algorithm is HashAlgorithm.BLAKE2B:
        return hashlib.blake2b(payload, digest_size=int(config.digest_bytes)).digest()
    return hashlib.sha256(payload).digest()[: int(config.digest_bytes)]


def split_membership_for_draw(draw: float, ratios: RandomRatios) -> SplitMembership:
    cumulative = 0.0
    for membership, ratio in ratios.ordered():
        cumulative += float(ratio)
        if draw < cumulative:
            return membership
    return ratios.ordered()[-1][0]


def encoded_feature_name(column: str, category: str, naming: EncodedFeatureNaming) -> str:
    if naming is EncodedFeatureNaming.COLUMN_EQUALS_CATEGORY:
        return f"{column}={category}"
    raise ValueError(f"unsupported encoded feature naming '{naming.value}'")


def ciciot_equivalence_digest(
    is_attack: bool,
    numeric_values: tuple[float, ...],
    config: HashConfig,
) -> bytes:
    payload = bytes((int(is_attack),)) + struct.pack(f"!{len(numeric_values)}d", *numeric_values)
    if config.algorithm is HashAlgorithm.BLAKE2B:
        return hashlib.blake2b(payload, digest_size=int(config.digest_bytes)).digest()
    return hashlib.sha256(payload).digest()[: int(config.digest_bytes)]


def edge_content_digest(
    numeric_values: tuple[float, ...],
    categorical_values: tuple[str | None, ...],
    config: HashConfig,
) -> bytes:
    payload = repr((numeric_values, categorical_values)).encode("utf-8")
    if config.algorithm is HashAlgorithm.BLAKE2B:
        return hashlib.blake2b(payload, digest_size=int(config.digest_bytes)).digest()
    return hashlib.sha256(payload).digest()[: int(config.digest_bytes)]
