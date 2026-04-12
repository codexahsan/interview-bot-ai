# backend/app/shared/utils/compliance_agent.py

"""
Compliance agent that masks PII before processing.
"""

from backend.app.shared.utils.pii_helper import mask_pii_data
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


class ComplianceAgent:
    """Applies PII masking to ensure compliance."""

    def process(self, raw_text: str) -> str:
        """
        Mask PII in the given text and return safe version.

        Args:
            raw_text: Unprocessed text possibly containing PII.

        Returns:
            Masked text with PII replaced by tokens.
        """
        logger.debug("ComplianceAgent processing text for PII masking")
        masked_text, _ = mask_pii_data(raw_text)
        return masked_text