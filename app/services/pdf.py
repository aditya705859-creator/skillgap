"""
PDF extraction service using PyMuPDF (fitz).
Handles text extraction with section detection.
"""
import io
import re
from typing import Optional
import fitz  # PyMuPDF


# Resume section headers to detect
SECTION_PATTERNS = {
    "skills": re.compile(
        r"^\s*(technical\s+)?skills?|competencies|technologies|tools|expertise",
        re.IGNORECASE,
    ),
    "experience": re.compile(
        r"^\s*(work\s+)?experience|employment|career|professional\s+background|work\s+history",
        re.IGNORECASE,
    ),
    "projects": re.compile(
        r"^\s*projects?|side\s+projects?|portfolio|personal\s+projects?",
        re.IGNORECASE,
    ),
    "education": re.compile(
        r"^\s*education|academic|qualifications?|degrees?",
        re.IGNORECASE,
    ),
    "summary": re.compile(
        r"^\s*summary|objective|profile|about\s+me|overview",
        re.IGNORECASE,
    ),
}


def extract_pdf_text(file_bytes: bytes) -> dict:
    """
    Extract text from a PDF file.

    Returns a dict with:
      - text: full plain text
      - sections: dict mapping section_name -> text
      - page_count: int
      - word_count: int
      - error: str or None
    """
    result = {
        "text": "",
        "sections": {k: "" for k in SECTION_PATTERNS},
        "page_count": 0,
        "word_count": 0,
        "error": None,
    }

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        result["error"] = f"Could not open PDF: {e}"
        return result

    result["page_count"] = len(doc)

    if len(doc) == 0:
        result["error"] = "The PDF has no pages."
        return result

    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"

    doc.close()

    if not full_text.strip():
        result["error"] = (
            "No text found in this PDF. It may be a scanned image. "
            "Please upload a text-based PDF."
        )
        return result

    # Clean text: collapse excessive whitespace
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    result["text"] = full_text.strip()
    result["word_count"] = len(full_text.split())

    # Detect sections
    result["sections"] = _detect_sections(full_text)
    return result


def _detect_sections(text: str) -> dict:
    """
    Parse resume text into sections by detecting headers.
    Returns a dict: section_name -> text content of that section.
    """
    sections = {k: "" for k in SECTION_PATTERNS}
    # Also keep an 'other' bucket for non-sectioned text
    sections["other"] = ""

    lines = text.split("\n")
    current_section = "other"

    for line in lines:
        stripped = line.strip()
        matched = False
        for section_name, pattern in SECTION_PATTERNS.items():
            if pattern.match(stripped) and len(stripped) < 60:
                current_section = section_name
                matched = True
                break
        if not matched:
            sections[current_section] = sections.get(current_section, "") + line + "\n"

    return sections
