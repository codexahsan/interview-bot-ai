# backend/app/shared/utils/pii_helper.py

"""
PII detection, masking, and restoration using Presidio and a JSON vault.
"""

import json
import os

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

from backend.app.constants import PII_MAPPINGS_FILE, PII_REDIS_KEY_PREFIX
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


class PIIVault:
    """Redis-based storage for PII token <-> original value mappings."""

    def __init__(self):
        from backend.app.core.redis_client import get_redis
        self.redis = get_redis()

    def _get_key(self, resume_id: str) -> str:
        """Generate a storage key for a given resume ID."""
        return f"pii_vault:{resume_id}"

    def store_new_mapping(self, resume_id: str, mapping: dict) -> None:
        """Persist token-to-original mapping in Redis."""
        key = self._get_key(resume_id)
        # Redis mein JSON string bana kar save karein
        self.redis.set(key, json.dumps(mapping), ex=7200) # 2 hours cache
        logger.info(f"Stored PII mapping in REDIS for resume {resume_id}")

    def restore_pii(self, resume_id: str, masked_text: str) -> str:
        """Replace tokens in masked text with original PII values from Redis."""
        key = self._get_key(resume_id)
        raw_mapping = self.redis.get(key)

        if not raw_mapping:
            logger.warning(f"No PII mapping found in Redis for resume {resume_id}")
            return masked_text

        mapping = json.loads(raw_mapping)
        unmasked_text = masked_text

        for token in sorted(mapping.keys(), key=len, reverse=True):
            unmasked_text = unmasked_text.replace(token, mapping[token])

        logger.debug(f"Restored PII from REDIS for resume {resume_id}")
        return unmasked_text


# Singleton instance
pii_vault = PIIVault()


# ---------------- PII MASKING ---------------- #

# Pakistan phone number pattern
pk_phone_pattern = Pattern(
    name="pk_phone_pattern",
    regex=r"(\+92|0|92)[-\s]?3[0-9]{2}[-\s]?[0-9]{7}",
    score=0.95
)

pk_phone_recognizer = PatternRecognizer(
    supported_entity="PHONE_NUMBER",
    patterns=[pk_phone_pattern]
)

analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(pk_phone_recognizer)

anonymizer = AnonymizerEngine()

# Whitelist of technical terms that should not be masked
WHITELIST = {
    "docker", "aws", "python", "fastapi", "linux", "bash",
    "nginx", "github", "cicd", "kubernetes", "react",
    "node", "postgresql", "mysql", "redis"
}


def mask_pii_data(text: str):
    """
    Detect and mask PII in text, returning masked text and token mapping.

    Args:
        text: Raw text possibly containing PII.

    Returns:
        Tuple of (masked_text, mapping_dict).
    """
    analysis_results = analyzer.analyze(
        text=text,
        entities=[
            "PERSON",
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "LOCATION",
            "URL",
            "ORGANIZATION"
        ],
        language="en"
    )

    # Filter out whitelisted technical terms
    filtered_results = [
        r for r in analysis_results
        if text[r.start:r.end].lower() not in WHITELIST
    ]

    mapping = {}
    entity_counts = {}

    # Sort by start index descending to avoid offset issues when replacing
    sorted_results = sorted(filtered_results, key=lambda x: x.start, reverse=True)
    masked_text = text

    for res in sorted_results:
        entity = res.entity_type
        entity_counts[entity] = entity_counts.get(entity, 0) + 1

        token = f"<{entity}_{entity_counts[entity]}>"
        original_value = text[res.start:res.end]

        mapping[token] = original_value
        masked_text = masked_text[:res.start] + token + masked_text[res.end:]

    logger.debug(f"Masked {len(mapping)} PII entities")
    return masked_text, mapping