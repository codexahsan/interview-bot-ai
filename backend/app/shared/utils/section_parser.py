# backend/app/shared/utils/section_parser.py

"""
Hybrid resume section detection: rule-based with LLM fallback.
"""

import re

from backend.app.shared.llm.client import get_llm
from backend.app.constants import (
    KNOWN_RESUME_SECTIONS,
    MIN_SECTION_COUNT_FOR_VALID,
    DUPLICATE_SECTION_THRESHOLD_RATIO,
    LLM_PARSE_TEXT_LIMIT,
    SECTION_PARSE_REGEX_PATTERN,
)
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


def is_valid_section_output(sections: list) -> bool:
    """
    Validate that rule-based parsing produced reasonable section structure.

    Args:
        sections: List of section strings with "Title\nContent" format.

    Returns:
        True if parsing seems valid, else False.
    """
    if len(sections) < MIN_SECTION_COUNT_FOR_VALID:
        return False

    titles = [s.split("\n")[0].lower() for s in sections]
    unique_titles = set(titles)

    # Too many duplicate sections indicates poor parsing
    if len(unique_titles) < len(sections) * DUPLICATE_SECTION_THRESHOLD_RATIO:
        return False

    return True


def rule_based_sections(text: str) -> list:
    """
    Split resume text using known section headings as delimiters.

    Args:
        text: Raw resume text.

    Returns:
        List of formatted sections ("Title\nContent").
    """
    pattern = r"(?im)^(" + "|".join(KNOWN_RESUME_SECTIONS) + r")\s*$"
    splits = re.split(pattern, text)

    if len(splits) == 1:
        # No strict headings found; return whole text as one section
        logger.debug("No known section headings found via rule-based parser")
        return [text]

    sections = []
    for i in range(1, len(splits), 2):
        title = splits[i].strip()
        content = splits[i + 1].strip() if i + 1 < len(splits) else ""
        sections.append(f"{title}\n{content}")

    logger.info(f"Rule-based parser extracted {len(sections)} sections")
    return sections


def llm_detect_sections(text: str) -> str:
    """
    Use LLM to identify sections when rule-based parser fails.

    Args:
        text: Raw resume text (first 3000 chars).

    Returns:
        LLM output containing "Section: ... Content: ..." blocks.
    """
    llm = get_llm()
    prompt = f"""
You are an expert resume parser.

Extract logical sections from this resume.

Rules:
- Merge broken lines into proper sentences
- Fix formatting issues mentally
- Identify real sections even if headings are messy
- Ignore duplicate or meaningless sections

Return ONLY:
Section: <name>
Content: <clean text>

Resume:
{text[:LLM_PARSE_TEXT_LIMIT]}
"""
    response = llm.invoke(prompt)
    logger.info("LLM fallback section detection invoked")
    return response.content


def parse_llm_sections(output: str) -> list:
    """
    Parse LLM output into structured sections.

    Args:
        output: Raw LLM response with Section/Content blocks.

    Returns:
        List of formatted sections ("Title\nContent").
    """
    matches = re.findall(SECTION_PARSE_REGEX_PATTERN, output, re.DOTALL)
    sections = []
    for title, content in matches:
        sections.append(f"{title.strip()}\n{content.strip()}")
    logger.info(f"Parsed {len(sections)} sections from LLM output")
    return sections


def get_structured_sections(text: str) -> list:
    """
    Main hybrid section detector: rule-based first, LLM fallback if invalid.

    Args:
        text: Raw resume text.

    Returns:
        List of structured section strings.
    """
    sections = rule_based_sections(text)

    if is_valid_section_output(sections):
        return sections

    logger.warning("Rule-based section parsing failed validation; falling back to LLM")
    llm_output = llm_detect_sections(text)
    sections = parse_llm_sections(llm_output)
    return sections