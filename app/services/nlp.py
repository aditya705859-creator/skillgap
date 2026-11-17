"""
NLP service – skill extraction from resume and job description.

Key design decisions:
1. Word-boundary regex prevents "Excel" matching "excellent", "Java" in "JavaScript",
   "Git" in "digital", "ML" in "HTML", "R" in random words.
2. Special cases: C++, C#, Node.js, CI/CD, scikit-learn handled with pre-escaping.
3. Confidence is higher when a skill appears in a Skills section or project context.
4. Each skill match carries the evidence sentence for transparency.
"""
import re
import csv
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Path to skills CSV
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SKILLS_CSV = DATA_DIR / "skills.csv"


# ---------------------------------------------------------------------------
# Skill alias map  (loaded once at import time)
# ---------------------------------------------------------------------------
class SkillRegistry:
    """Loads skills.csv and builds regex patterns for each skill."""

    def __init__(self):
        self.skills: List[Dict] = []          # raw rows from CSV
        self.patterns: List[Tuple] = []       # (skill_name, regex_pattern, row)
        self._load()

    def _load(self):
        if not SKILLS_CSV.exists():
            return
        with open(SKILLS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.skills.append(row)
                # Build all variants: canonical name + all aliases
                variants = [row["skill_name"]] + [
                    a.strip() for a in row.get("aliases", "").split("|") if a.strip()
                ]
                pattern = self._build_pattern(variants, row["skill_name"])
                if pattern:
                    self.patterns.append((row["skill_name"], pattern, row))

    @staticmethod
    def _escape_special(term: str) -> str:
        """Escape regex special chars, then handle C++/C# / Node.js boundaries."""
        # Escape everything first
        t = re.escape(term)
        # re.escape turns + into \+, # into \#, . into \. — that's fine
        return t

    @staticmethod
    def _word_boundary(term_re: str, raw_term: str = "") -> str:
        """
        Wrap a regex term in appropriate word boundaries.
        For terms ending/starting with non-word chars (C++, C#, Node.js, CI/CD)
        we use look-arounds instead of raw \\b so we don't get false positives.
        """
        if raw_term.strip().lower() == "r":
            return r"(?<![A-Za-z0-9_&/+\-\.])" + term_re + r"(?![A-Za-z0-9_&/+\-\.])"
        # Left boundary: preceded by start, whitespace, or punctuation
        left = r"(?<![A-Za-z0-9_])"
        # Right boundary: followed by end, whitespace, or punctuation (not word char)
        right = r"(?![A-Za-z0-9_])"
        return left + term_re + right

    def _build_pattern(self, variants: List[str], skill_name: str) -> Optional[re.Pattern]:
        """Build a combined regex for all variants of a skill."""
        # Sort longest first so "scikit-learn" beats "scikit"
        variants_sorted = sorted(set(variants), key=len, reverse=True)
        parts = []
        for v in variants_sorted:
            if not v:
                continue
            escaped = self._escape_special(v)
            parts.append(self._word_boundary(escaped, v))
        if not parts:
            return None
        combined = "|".join(parts)
        try:
            return re.compile(combined, re.IGNORECASE)
        except re.error:
            return None


# Singleton registry
_registry: Optional[SkillRegistry] = None


def get_registry(force_reload: bool = False) -> SkillRegistry:
    global _registry
    if _registry is None or force_reload:
        _registry = SkillRegistry()
    return _registry


# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------
def _split_sentences(text: str) -> List[str]:
    """Split text into sentences (simple heuristic)."""
    sentences = re.split(r"(?<=[.!?])\s+|\n", text)
    return [s.strip() for s in sentences if s.strip()]


# ---------------------------------------------------------------------------
# Skill extraction from resume text
# ---------------------------------------------------------------------------
def extract_skills_from_resume(
    sections: Dict[str, str],
    full_text: str,
) -> List[Dict]:
    """
    Extract skills from a resume.

    Returns a list of dicts:
      { name, category, confidence, evidence, section, skill_row }
    """
    registry = get_registry()
    found: Dict[str, Dict] = {}  # skill_name -> best match info

    # Section weights for confidence scoring
    section_weights = {
        "skills": 1.0,
        "projects": 0.85,
        "experience": 0.75,
        "summary": 0.65,
        "education": 0.55,
        "other": 0.5,
    }

    sentences = _split_sentences(full_text)
    # Build sentence→section map
    sentence_sections: Dict[str, str] = {}
    for section_name, section_text in sections.items():
        for s in _split_sentences(section_text):
            sentence_sections[s] = section_name

    for skill_name, pattern, row in registry.patterns:
        best_conf = 0.0
        best_evidence = ""
        best_section = "other"

        for sentence in sentences:
            if pattern.search(sentence):
                sec = sentence_sections.get(sentence, "other")
                conf = section_weights.get(sec, 0.5)
                if conf > best_conf:
                    best_conf = conf
                    best_evidence = sentence[:200]
                    best_section = sec

        if best_conf > 0:
            if skill_name not in found or found[skill_name]["confidence"] < best_conf:
                found[skill_name] = {
                    "name": skill_name,
                    "category": row.get("category", "Other"),
                    "confidence": round(best_conf, 2),
                    "evidence": best_evidence,
                    "section": best_section,
                    "difficulty": row.get("difficulty", "Intermediate"),
                    "learning_hours": int(row.get("learning_hours", 50)),
                    "prerequisites": [
                        p.strip()
                        for p in row.get("prerequisites", "").split("|")
                        if p.strip()
                    ],
                }

    return list(found.values())


# ---------------------------------------------------------------------------
# Skill extraction from job description
# ---------------------------------------------------------------------------

# Cue phrases that indicate required vs preferred skills
_REQUIRED_CUES = re.compile(
    r"\b(must\s+have|required|mandatory|essential|need|needs|experience\s+with|proficient\s+in|strong\s+knowledge)\b",
    re.IGNORECASE,
)
_PREFERRED_CUES = re.compile(
    r"\b(nice\s+to\s+have|preferred|plus|bonus|desirable|advantage|ideally|familiar\s+with|exposure\s+to)\b",
    re.IGNORECASE,
)


def extract_skills_from_jd(jd_text: str) -> Dict[str, List[Dict]]:
    """
    Extract required and preferred skills from a job description.

    Returns:
      {
        "required": [ {name, category, ...}, ... ],
        "preferred": [ {name, category, ...}, ... ],
        "all": [ ... ],
      }
    """
    registry = get_registry()
    required: Dict[str, Dict] = {}
    preferred: Dict[str, Dict] = {}

    sentences = _split_sentences(jd_text)

    for skill_name, pattern, row in registry.patterns:
        for sentence in sentences:
            if pattern.search(sentence):
                is_required = bool(_REQUIRED_CUES.search(sentence))
                is_preferred = bool(_PREFERRED_CUES.search(sentence))

                skill_info = {
                    "name": skill_name,
                    "category": row.get("category", "Other"),
                    "importance": "preferred" if is_preferred and not is_required else "required",
                    "evidence": sentence[:200],
                    "difficulty": row.get("difficulty", "Intermediate"),
                    "learning_hours": int(row.get("learning_hours", 50)),
                    "prerequisites": [
                        p.strip()
                        for p in row.get("prerequisites", "").split("|")
                        if p.strip()
                    ],
                }

                if is_preferred and not is_required:
                    preferred.setdefault(skill_name, skill_info)
                else:
                    required.setdefault(skill_name, skill_info)
                break

    # Combine: skills that appear in both — keep required
    for k in list(preferred.keys()):
        if k in required:
            del preferred[k]

    all_skills = list(required.values()) + list(preferred.values())
    return {
        "required": list(required.values()),
        "preferred": list(preferred.values()),
        "all": all_skills,
    }
