"""
Report generation service – creates a PDF report using ReportLab.
"""
import io
import datetime
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.pdfgen import canvas as pdfcanvas

# Brand colours
TEAL = colors.HexColor("#0D9488")
TEAL_LIGHT = colors.HexColor("#CCFBF1")
GREEN = colors.HexColor("#059669")
AMBER = colors.HexColor("#D97706")
RED = colors.HexColor("#DC2626")
DARK = colors.HexColor("#0F172A")
GREY = colors.HexColor("#475569")
LIGHT_GREY = colors.HexColor("#F5F5F4")
BORDER = colors.HexColor("#E2E8F0")


def _make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "SGTitle", parent=styles["Title"],
        fontName="Helvetica-Bold", fontSize=24, textColor=DARK,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "SGSubtitle", parent=styles["Normal"],
        fontName="Helvetica", fontSize=11, textColor=GREY,
        spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        "SGH2", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=14, textColor=DARK,
        spaceBefore=16, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "SGH3", parent=styles["Heading3"],
        fontName="Helvetica-Bold", fontSize=11, textColor=GREY,
        spaceBefore=8, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "SGBody", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, textColor=DARK,
        spaceAfter=4, leading=14,
    ))
    styles.add(ParagraphStyle(
        "SGCaption", parent=styles["Normal"],
        fontName="Helvetica-Oblique", fontSize=9, textColor=GREY,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "SGBullet", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10, textColor=DARK,
        leftIndent=16, spaceAfter=3, bulletIndent=6, leading=14,
    ))
    return styles


def generate_pdf_report(analysis: Dict, user_name: str) -> bytes:
    """
    Generate a PDF report for an analysis.

    Parameters
    ----------
    analysis : Analysis ORM object (or dict-like) with all fields
    user_name : user's display name

    Returns bytes of the PDF.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
        title=f"SkillGap Report – {analysis.target_role or 'Analysis'}",
    )

    styles = _make_styles()
    story = []

    results = analysis.results_json or {}
    score = analysis.score or 0
    grade = analysis.grade or "F"
    role = analysis.target_role or "Role"

    # ---------------------------------------------------------------------------
    # Header
    # ---------------------------------------------------------------------------
    story.append(Paragraph("SkillGap Report", styles["SGTitle"]))
    story.append(Paragraph(
        f"Prepared for: <b>{user_name}</b> &nbsp;|&nbsp; "
        f"Role: <b>{role}</b> &nbsp;|&nbsp; "
        f"Date: {datetime.date.today().strftime('%d %b %Y')}",
        styles["SGSubtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=16))

    # ---------------------------------------------------------------------------
    # Score summary table
    # ---------------------------------------------------------------------------
    story.append(Paragraph("Score Summary", styles["SGH2"]))

    grade_color = GREEN if grade == "A" else (TEAL if grade == "B" else (AMBER if grade == "C" else RED))
    counts = results.get("counts", {})
    breakdown = results.get("score_breakdown", {})

    summary_data = [
        ["Overall score", f"{score:.0f} / 100", "Grade", grade],
        ["Matched skills", str(counts.get("matched", 0)), "Partial matches", str(counts.get("partial", 0))],
        ["Missing skills", str(counts.get("missing", 0)), "Total JD skills", str(counts.get("total_jd", 0))],
    ]
    summary_table = Table(summary_data, colWidths=[4 * cm, 3.5 * cm, 4 * cm, 3.5 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL_LIGHT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUND", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # Verdict
    if results.get("verdict"):
        story.append(Paragraph(f"<b>Verdict:</b> {results['verdict']}", styles["SGBody"]))
    story.append(Spacer(1, 8))

    # Score breakdown
    story.append(Paragraph("Score Breakdown", styles["SGH3"]))
    bd_data = [["Component", "Weight", "Points earned"]]
    component_labels = {
        "exact_match": "Exact skill matches (60%)",
        "partial_match": "Partial matches (20%)",
        "category_coverage": "Category coverage (10%)",
        "resume_quality": "Resume quality (10%)",
    }
    for key, label in component_labels.items():
        bd_data.append([label, "", f"{breakdown.get(key, 0):.1f}"])
    bd_data.append(["Total", "", f"{breakdown.get('total', score):.1f}"])

    bd_table = Table(bd_data, colWidths=[8 * cm, 3 * cm, 4 * cm])
    bd_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), TEAL_LIGHT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
    ]))
    story.append(bd_table)
    story.append(Spacer(1, 16))

    # ---------------------------------------------------------------------------
    # Matched skills
    # ---------------------------------------------------------------------------
    matched = results.get("matched_skills", [])
    if matched:
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8))
        story.append(Paragraph("Matched Skills", styles["SGH2"]))
        story.append(Paragraph(
            f"You have {len(matched)} of the required skills.",
            styles["SGCaption"],
        ))
        matched_names = [s["name"] for s in matched]
        # Format as comma-separated chips
        story.append(Paragraph(", ".join(matched_names), styles["SGBody"]))
        story.append(Spacer(1, 12))

    # ---------------------------------------------------------------------------
    # Missing skills
    # ---------------------------------------------------------------------------
    missing = results.get("missing_skills", [])
    if missing:
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8))
        story.append(Paragraph("Skills to Develop", styles["SGH2"]))
        for m in missing[:10]:
            importance = "Required" if m.get("importance") == "required" else "Preferred"
            story.append(Paragraph(
                f"• <b>{m['name']}</b> ({importance}) — {m.get('category', '')}",
                styles["SGBullet"],
            ))
        story.append(Spacer(1, 12))

    # ---------------------------------------------------------------------------
    # Learning roadmap
    # ---------------------------------------------------------------------------
    roadmap = results.get("roadmap", [])
    if roadmap:
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8))
        story.append(Paragraph("Learning Roadmap", styles["SGH2"]))
        story.append(Paragraph(
            "Skills are ordered from foundational to advanced, respecting prerequisites.",
            styles["SGCaption"],
        ))
        rm_data = [["#", "Skill", "Difficulty", "Est. hours", "Project"]]
        for i, item in enumerate(roadmap[:8], 1):
            rm_data.append([
                str(i),
                item.get("skill", ""),
                item.get("difficulty", "").capitalize(),
                str(item.get("hours", "")),
                item.get("project_name", "") or "—",
            ])
        rm_table = Table(rm_data, colWidths=[0.8 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm, 5 * cm])
        rm_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
            ("ROWBACKGROUND", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ]))
        story.append(rm_table)
        story.append(Spacer(1, 16))

    # ---------------------------------------------------------------------------
    # Top matching roles
    # ---------------------------------------------------------------------------
    top_roles = results.get("top_roles", [])
    if top_roles:
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8))
        story.append(Paragraph("Top Matching Roles", styles["SGH2"]))
        for r in top_roles[:5]:
            story.append(Paragraph(
                f"• <b>{r['role']}</b> — {r['score']:.0f}% match",
                styles["SGBullet"],
            ))
        story.append(Spacer(1, 12))

    # ---------------------------------------------------------------------------
    # Methodology note
    # ---------------------------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8))
    story.append(Paragraph("Methodology", styles["SGH2"]))
    methodology = (
        "SkillGap extracts skills from your resume using word-boundary regex against a curated "
        "skill database (84+ skills). It detects sections (Skills, Experience, Projects, Education) "
        "and assigns higher confidence to skills mentioned in Skills or Projects sections. "
        "Skill matching uses exact match (60% weight), TF-IDF cosine partial match (20%), "
        "category coverage (10%), and resume quality signals (10%). "
        "The score is a measure of resume–JD skill overlap and is NOT a prediction of hiring outcomes. "
        "Learning roadmap ordering uses topological sort of a prerequisite graph (networkx). "
        "Role-fit ranking uses cosine similarity of weighted skill vectors."
    )
    story.append(Paragraph(methodology, styles["SGBody"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<i>This report is generated automatically. The score reflects keyword and skill overlap "
        "and should be used as a guide, not a definitive hiring assessment.</i>",
        styles["SGCaption"],
    ))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=6))
    story.append(Paragraph(
        f"Generated by SkillGap &nbsp;|&nbsp; {datetime.datetime.now().strftime('%d %b %Y %H:%M')}",
        ParagraphStyle("Footer", fontName="Helvetica", fontSize=8, textColor=GREY, alignment=TA_CENTER),
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
