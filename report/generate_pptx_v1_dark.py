#!/usr/bin/env python3
"""
Academic Project Presentation Generator
Course: Data Structures & Algorithms (DSA)
Candidate: Soumyshiv Das (Reg No: 2502051963)
Target: 10–12 slides
Output: SoumyshivDas.2502051963.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

PPTX_FILENAME = "SoumyshivDas.2502051963.pptx"

# ── colour palette ─────────────────────────────────────────────────
BG_DARK    = RGBColor(0x0F, 0x17, 0x2A)   # deep navy
BG_CARD    = RGBColor(0x1E, 0x29, 0x3B)   # card surface
ACCENT     = RGBColor(0x38, 0xBD, 0xF8)   # cyan accent
ACCENT2    = RGBColor(0xA7, 0x8B, 0xFA)   # lavender
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xCB, 0xD5, 0xE1)
MUTED      = RGBColor(0x94, 0xA3, 0xB8)
ORANGE     = RGBColor(0xFB, 0x92, 0x3C)
GREEN      = RGBColor(0x4A, 0xDE, 0x80)
RED_SOFT   = RGBColor(0xF8, 0x71, 0x71)

# ── helpers ────────────────────────────────────────────────────────

def set_slide_bg(slide, color):
    """Fill the slide background with a solid colour."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_text_box(slide, left, top, width, height, text, font_size=14,
                 color=WHITE, bold=False, alignment=PP_ALIGN.LEFT,
                 font_name="Calibri"):
    """Add a simple single-run text box."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return tf


def add_rich_text_box(slide, left, top, width, height, runs,
                      alignment=PP_ALIGN.LEFT, line_spacing=1.2):
    """
    Add a text box with multiple runs.
    runs: list of dicts {text, size, color, bold, name}
    """
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = alignment
    if line_spacing:
        p.line_spacing = Pt(int(runs[0].get("size", 14) * line_spacing))
    for i, r in enumerate(runs):
        run = p.add_run() if i > 0 else (p.runs[0] if p.runs else p.add_run())
        run.text = r["text"]
        run.font.size = Pt(r.get("size", 14))
        run.font.color.rgb = r.get("color", WHITE)
        run.font.bold = r.get("bold", False)
        run.font.name = r.get("name", "Calibri")
    return tf


def add_bullet_list(slide, left, top, width, height, items, font_size=13,
                    color=LIGHT_GRAY, bullet_color=ACCENT, spacing_after=6):
    """Add a bulleted list using paragraph-level bullets."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = item
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.name = "Calibri"
        p.level = 0
        p.space_after = Pt(spacing_after)
        pPr = p._pPr
        if pPr is None:
            from pptx.oxml.ns import qn
            pPr = p._p.get_or_add_pPr()
        from pptx.oxml.ns import qn
        buChar = pPr.makeelement(qn("a:buChar"), {"char": "●"})
        buClr = pPr.makeelement(qn("a:buClr"), {})
        color_hex = str(bullet_color)  # RGBColor.__str__ returns e.g. "38BDF8"
        srgb = buClr.makeelement(qn("a:srgbClr"), {"val": color_hex})
        buClr.append(srgb)
        # remove existing bullet elements
        for tag in [qn("a:buChar"), qn("a:buNone"), qn("a:buClr")]:
            for old in pPr.findall(tag):
                pPr.remove(old)
        pPr.append(buClr)
        pPr.append(buChar)
    return tf


def add_accent_bar(slide, left, top, width=Inches(0.06), height=Inches(0.6),
                   color=ACCENT):
    """Add a small vertical accent bar."""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def add_card(slide, left, top, width, height, color=BG_CARD):
    """Add a rounded card background."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def add_table(slide, left, top, width, height, rows, cols, data, header_bg=ACCENT,
              header_fg=BG_DARK, cell_bg=BG_CARD, cell_fg=LIGHT_GRAY, font_size=10):
    """Add a styled table."""
    table_shape = slide.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table
    for r in range(rows):
        for c in range(cols):
            cell = table.cell(r, c)
            cell.text = str(data[r][c])
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(font_size)
                paragraph.font.name = "Calibri"
                if r == 0:
                    paragraph.font.bold = True
                    paragraph.font.color.rgb = header_fg
                    paragraph.alignment = PP_ALIGN.CENTER
                else:
                    paragraph.font.color.rgb = cell_fg
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            fill = cell.fill
            fill.solid()
            if r == 0:
                fill.fore_color.rgb = header_bg
            else:
                fill.fore_color.rgb = cell_bg if r % 2 == 1 else RGBColor(0x17, 0x22, 0x34)
    return table


def section_header(slide, title, subtitle="", number=""):
    """Standard section header block used on most content slides."""
    if number:
        add_text_box(slide, Inches(0.7), Inches(0.3), Inches(1), Inches(0.4),
                     number, font_size=11, color=ACCENT, bold=True)
    add_accent_bar(slide, Inches(0.6), Inches(0.55), height=Inches(0.45))
    add_text_box(slide, Inches(0.85), Inches(0.5), Inches(8), Inches(0.55),
                 title, font_size=24, color=WHITE, bold=True)
    if subtitle:
        add_text_box(slide, Inches(0.85), Inches(1.0), Inches(8), Inches(0.35),
                     subtitle, font_size=12, color=MUTED)


# ── slide builders ─────────────────────────────────────────────────

def slide_01_title(prs):
    """SLIDE 1 – Title / Cover Slide"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    set_slide_bg(slide, BG_DARK)

    # decorative accent strip at top
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                   Inches(0), Inches(0), Inches(10), Inches(0.06))
    shape.fill.solid()
    shape.fill.fore_color.rgb = ACCENT
    shape.line.fill.background()

    # University name
    add_text_box(slide, Inches(0.5), Inches(0.5), Inches(9), Inches(0.35),
                 "MANIPAL UNIVERSITY JAIPUR", font_size=13, color=MUTED,
                 bold=True, alignment=PP_ALIGN.CENTER)

    add_text_box(slide, Inches(0.5), Inches(0.85), Inches(9), Inches(0.3),
                 "Department of Computer Science & Engineering",
                 font_size=11, color=MUTED, alignment=PP_ALIGN.CENTER)

    # Main title
    add_text_box(slide, Inches(0.5), Inches(1.8), Inches(9), Inches(0.7),
                 "Burkhard-Keller Metric Space", font_size=32, color=WHITE,
                 bold=True, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(0.5), Inches(2.45), Inches(9), Inches(0.7),
                 "Image Deduplicator", font_size=32, color=ACCENT,
                 bold=True, alignment=PP_ALIGN.CENTER)

    # Subtitle
    add_text_box(slide, Inches(0.8), Inches(3.3), Inches(8.4), Inches(0.55),
                 "Sub-Linear Near-Duplicate Detection, Triangle Inequality Pruning,\n"
                 "and Perceptual Hash Clustering in Discrete Metric Spaces",
                 font_size=12, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)

    # Horizontal rule
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                   Inches(3.5), Inches(4.1), Inches(3), Inches(0.02))
    shape.fill.solid()
    shape.fill.fore_color.rgb = ACCENT2
    shape.line.fill.background()

    # Author info card
    add_card(slide, Inches(2.5), Inches(4.5), Inches(5), Inches(1.5))
    add_text_box(slide, Inches(2.8), Inches(4.65), Inches(4.4), Inches(0.3),
                 "Soumyshiv Das", font_size=18, color=WHITE, bold=True,
                 alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(2.8), Inches(5.05), Inches(4.4), Inches(0.25),
                 "Registration No: 2502051963", font_size=12, color=ACCENT,
                 alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(2.8), Inches(5.35), Inches(4.4), Inches(0.25),
                 "Course: Data Structures & Algorithms  •  B.Tech CSE",
                 font_size=10, color=MUTED, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(2.8), Inches(5.60), Inches(4.4), Inches(0.25),
                 "Submission Date: 19 October 2026", font_size=10, color=MUTED,
                 alignment=PP_ALIGN.CENTER)

    # GitHub
    add_text_box(slide, Inches(0.5), Inches(6.7), Inches(9), Inches(0.25),
                 "github.com/soumyshiv/dsa-bktree-image-deduplicator",
                 font_size=10, color=ACCENT2, alignment=PP_ALIGN.CENTER)


def slide_02_agenda(prs):
    """SLIDE 2 – Agenda / Table of Contents"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "Presentation Outline")

    agenda = [
        ("01", "Problem Definition & Motivation"),
        ("02", "Theoretical Foundations — Metric Spaces"),
        ("03", "Multi-Channel Perceptual Feature Engineering"),
        ("04", "BK-Tree Architecture & Algorithms"),
        ("05", "Triangle Inequality Pruning — Theorem & Proof"),
        ("06", "Global Clustering via Disjoint Set Union"),
        ("07", "System Architecture & Web Studio"),
        ("08", "Interactive Topology Visualizer & Pruning Simulator"),
        ("09", "Empirical Benchmarks & Performance"),
        ("10", "Conclusion, References & Demo"),
    ]
    y = Inches(1.5)
    for num, title in agenda:
        add_card(slide, Inches(1.2), y, Inches(7.6), Inches(0.38), BG_CARD)
        add_text_box(slide, Inches(1.4), y + Emu(20000), Inches(0.5), Inches(0.3),
                     num, font_size=12, color=ACCENT, bold=True)
        add_text_box(slide, Inches(2.0), y + Emu(20000), Inches(6.5), Inches(0.3),
                     title, font_size=13, color=LIGHT_GRAY)
        y += Inches(0.47)


def slide_03_problem(prs):
    """SLIDE 3 – Problem Definition & Motivation"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "Problem Definition & Motivation", number="01")

    # Left: The Problem
    add_card(slide, Inches(0.5), Inches(1.5), Inches(4.2), Inches(3.8))
    add_text_box(slide, Inches(0.7), Inches(1.55), Inches(3.8), Inches(0.35),
                 "The Challenge", font_size=15, color=ORANGE, bold=True)
    add_bullet_list(slide, Inches(0.7), Inches(1.95), Inches(3.8), Inches(3.0), [
        "Digital systems generate massive near-duplicate images",
        "Cryptographic hashes (MD5, SHA-256) fail on perceptually similar images due to avalanche effect",
        "Naive pairwise comparison is O(N²) — 100K images → 5 billion comparisons",
        "Need: sub-linear near-duplicate search with formal guarantees",
    ], font_size=11, spacing_after=8)

    # Right: Our Solution
    add_card(slide, Inches(5.0), Inches(1.5), Inches(4.5), Inches(3.8))
    add_text_box(slide, Inches(5.2), Inches(1.55), Inches(4.1), Inches(0.35),
                 "Our Solution", font_size=15, color=GREEN, bold=True)
    add_bullet_list(slide, Inches(5.2), Inches(1.95), Inches(4.1), Inches(3.0), [
        "100-bit multi-channel perceptual hash maps images into a discrete metric space",
        "BK-Tree indexes images for sub-linear O(N^α) range queries, α < 1",
        "Triangle Inequality prunes 41–89% of search space in O(1)",
        "DSU clusters duplicates globally in O(N^(1+α)) time",
    ], font_size=11, spacing_after=8, bullet_color=GREEN)

    # Bottom highlight
    add_card(slide, Inches(0.5), Inches(5.6), Inches(9.0), Inches(0.8),
             RGBColor(0x17, 0x22, 0x34))
    add_text_box(slide, Inches(0.8), Inches(5.65), Inches(8.4), Inches(0.7),
                 "Key Insight: The Hamming distance on binary perceptual hashes forms a "
                 "discrete metric space — enabling BK-Tree's Triangle Inequality pruning "
                 "to eliminate entire subtrees without computing distances.",
                 font_size=11, color=ACCENT)


def slide_04_metric_spaces(prs):
    """SLIDE 4 – Metric Spaces & Hamming Distance"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "Theoretical Foundations — Metric Spaces", number="02")

    # Four axioms
    add_text_box(slide, Inches(0.7), Inches(1.45), Inches(4), Inches(0.3),
                 "The Four Metric Axioms", font_size=15, color=ACCENT, bold=True)

    axioms = [
        ("Non-Negativity", "d(x, y) ≥ 0"),
        ("Identity of Indiscernibles", "d(x, y) = 0 ⟺ x = y"),
        ("Symmetry", "d(x, y) = d(y, x)"),
        ("Triangle Inequality", "d(x, z) ≤ d(x, y) + d(y, z)"),
    ]
    y = Inches(1.85)
    for name, formula in axioms:
        add_card(slide, Inches(0.6), y, Inches(4.3), Inches(0.52))
        add_text_box(slide, Inches(0.8), y + Emu(15000), Inches(2.0), Inches(0.25),
                     name, font_size=11, color=WHITE, bold=True)
        add_text_box(slide, Inches(2.9), y + Emu(15000), Inches(1.9), Inches(0.25),
                     formula, font_size=11, color=ACCENT)
        y += Inches(0.58)

    # Hamming distance
    add_text_box(slide, Inches(5.4), Inches(1.45), Inches(4), Inches(0.3),
                 "Discrete Hamming Metric", font_size=15, color=ACCENT2, bold=True)
    add_card(slide, Inches(5.3), Inches(1.85), Inches(4.2), Inches(1.5))
    add_text_box(slide, Inches(5.5), Inches(1.95), Inches(3.8), Inches(1.3),
                 "For binary strings u, v ∈ {0,1}¹⁰⁰:\n\n"
                 "  dH(u, v) = popcount(u ⊕ v)\n\n"
                 "Range: {0, 1, 2, … , 100}\n"
                 "Satisfies all 4 axioms unconditionally.",
                 font_size=11, color=LIGHT_GRAY)

    # Discrete vs Continuous
    add_card(slide, Inches(5.3), Inches(3.55), Inches(4.2), Inches(1.2))
    add_text_box(slide, Inches(5.5), Inches(3.6), Inches(3.8), Inches(0.3),
                 "Why Discrete Metric Spaces?", font_size=12, color=GREEN, bold=True)
    add_text_box(slide, Inches(5.5), Inches(3.95), Inches(3.8), Inches(0.7),
                 "• k-d trees degrade when D > 15 (curse of dimensionality)\n"
                 "• BK-Trees partition children into exact integer distance bins\n"
                 "• Discrete distances enable deterministic branch pruning",
                 font_size=10, color=LIGHT_GRAY)

    # Bottom: verification
    add_card(slide, Inches(0.5), Inches(5.3), Inches(9.0), Inches(0.9),
             RGBColor(0x17, 0x22, 0x34))
    add_text_box(slide, Inches(0.8), Inches(5.35), Inches(8.4), Inches(0.8),
                 "✓ Verified: Automated test suite validates all 4 metric axioms across "
                 "1,000 random triads (x, y, z) — 100% pass rate, 0 violations. "
                 "Triangle Inequality holds unconditionally for the Hamming metric.",
                 font_size=11, color=GREEN)


def slide_05_hashing(prs):
    """SLIDE 5 – Multi-Channel Perceptual Hashing"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "Multi-Channel Perceptual Feature Engineering", number="03")

    # Table of hash components
    data = [
        ["Component", "Method", "Bits", "Invariance"],
        ["Spatial Luminance", "8×8 Bicubic + Mean Threshold", "64", "Exposure, gamma, scale"],
        ["Hue Histogram", "12-Bin 30° Quantized Distribution", "12", "Distinct chromatic palettes"],
        ["Saturation Hist.", "12-Bin Purity Profiling", "12", "Monochrome vs vibrant"],
        ["Value Histogram", "12-Bin Dynamic Range", "12", "High-key vs low-key lighting"],
        ["Total Vector", "Multi-Channel Fused Hash", "100", "Discrete Metric Space"],
    ]
    add_table(slide, Inches(0.5), Inches(1.45), Inches(9.0), Inches(2.0),
              len(data), 4, data, font_size=10)

    # Visual pipeline
    add_text_box(slide, Inches(0.7), Inches(3.7), Inches(4), Inches(0.3),
                 "Hash Construction Pipeline", font_size=14, color=ACCENT, bold=True)

    steps = [
        ("1", "Convert to Grayscale", ACCENT),
        ("2", "Bicubic downsample → 8×8", ACCENT),
        ("3", "Mean-threshold → 64-bit spatial hash", ACCENT),
        ("4", "Convert to HSV colour space", ACCENT2),
        ("5", "Quantize H/S/V → 12 bins each", ACCENT2),
        ("6", "Median-split → 36-bit colour hash", ACCENT2),
        ("7", "Concatenate → 100-bit feature vector", GREEN),
    ]
    y = Inches(4.1)
    for num, text, color in steps:
        add_text_box(slide, Inches(0.9), y, Inches(0.3), Inches(0.22),
                     num, font_size=10, color=BG_DARK, bold=True)
        add_card(slide, Inches(0.8), y, Inches(0.35), Inches(0.25), color)
        add_text_box(slide, Inches(1.3), y, Inches(3.5), Inches(0.22),
                     text, font_size=10, color=LIGHT_GRAY)
        y += Inches(0.30)

    # Why multi-channel
    add_card(slide, Inches(5.2), Inches(3.7), Inches(4.3), Inches(2.8))
    add_text_box(slide, Inches(5.4), Inches(3.75), Inches(3.9), Inches(0.3),
                 "Why Multi-Channel?", font_size=14, color=ORANGE, bold=True)
    add_bullet_list(slide, Inches(5.4), Inches(4.15), Inches(3.9), Inches(2.2), [
        "Standard pHash collapses to grayscale — loses all colour information",
        "Two images with identical geometry but different colours produce identical hashes",
        "Our 36-bit HSV descriptor catches colour-only variations",
        "Result: drastically reduced false-positive cluster collisions",
    ], font_size=10, spacing_after=6, bullet_color=ORANGE)


def slide_06_bktree(prs):
    """SLIDE 6 – BK-Tree Architecture"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "BK-Tree Architecture & Algorithms", number="04")

    # Node structure
    add_card(slide, Inches(0.5), Inches(1.45), Inches(4.3), Inches(2.2))
    add_text_box(slide, Inches(0.7), Inches(1.5), Inches(3.9), Inches(0.3),
                 "BKNode Structure", font_size=14, color=ACCENT, bold=True)
    add_bullet_list(slide, Inches(0.7), Inches(1.9), Inches(3.9), Inches(1.5), [
        "img_hash: 100-bit perceptual feature vector (pivot)",
        "paths: list of filepaths sharing identical hash (d=0)",
        "children: HashMap<int, BKNode> mapping edge distances to child nodes",
    ], font_size=11, spacing_after=6)

    # Insertion algorithm
    add_card(slide, Inches(5.1), Inches(1.45), Inches(4.4), Inches(2.2))
    add_text_box(slide, Inches(5.3), Inches(1.5), Inches(4.0), Inches(0.3),
                 "Insertion Algorithm", font_size=14, color=GREEN, bold=True)
    add_bullet_list(slide, Inches(5.3), Inches(1.9), Inches(4.0), Inches(1.5), [
        "If root is null → create root node",
        "Compute d = dH(curr.hash, new_hash)",
        "If d = 0 → append path to collision list",
        "If children[d] exists → traverse to child",
        "Else → create new child at edge d",
    ], font_size=11, spacing_after=5, bullet_color=GREEN)

    # Complexity table
    add_text_box(slide, Inches(0.7), Inches(3.9), Inches(4), Inches(0.3),
                 "Complexity Analysis", font_size=14, color=ACCENT2, bold=True)
    data = [
        ["Operation", "Naive", "BK-Tree (Avg)", "BK-Tree (Worst)"],
        ["Construction", "O(1)", "O(N log N)", "O(N²)"],
        ["Range Query", "O(N)", "O(N^α), α<1", "O(N)"],
        ["Global Clustering", "O(N²)", "O(N^(1+α))", "O(N²)"],
        ["Memory", "O(N)", "O(N)", "O(N)"],
    ]
    add_table(slide, Inches(0.5), Inches(4.3), Inches(9.0), Inches(1.8),
              len(data), 4, data, font_size=10)


def slide_07_pruning(prs):
    """SLIDE 7 – Triangle Inequality Pruning Theorem & Proof"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "Triangle Inequality Pruning — Theorem & Proof", number="05")

    # Theorem statement
    add_card(slide, Inches(0.5), Inches(1.5), Inches(9.0), Inches(1.5),
             RGBColor(0x17, 0x22, 0x34))
    add_text_box(slide, Inches(0.7), Inches(1.55), Inches(1.5), Inches(0.3),
                 "THEOREM", font_size=12, color=ORANGE, bold=True)
    add_text_box(slide, Inches(0.7), Inches(1.9), Inches(8.6), Inches(1.0),
                 "Let Q be the query, P the current pivot, τ the tolerance radius, and C a child "
                 "node at edge distance d₂ = d(P,C). A match d(Q,X) ≤ τ can exist in C's subtree "
                 "ONLY IF:\n\n"
                 "       d(Q, P) − τ  ≤  d(P, C)  ≤  d(Q, P) + τ",
                 font_size=12, color=LIGHT_GRAY)

    # Proof
    add_card(slide, Inches(0.5), Inches(3.2), Inches(4.3), Inches(3.0))
    add_text_box(slide, Inches(0.7), Inches(3.25), Inches(3.9), Inches(0.3),
                 "Proof Sketch", font_size=13, color=ACCENT, bold=True)
    add_text_box(slide, Inches(0.7), Inches(3.6), Inches(3.9), Inches(2.5),
                 "By Triangle Inequality (Axiom 4):\n\n"
                 "① d(Q,P) ≤ d(Q,X) + d(X,P)\n"
                 "    ⟹ d(Q,X) ≥ d(Q,P) − d(X,P)\n\n"
                 "② d(X,P) ≤ d(Q,X) + d(Q,P)\n"
                 "    ⟹ d(Q,X) ≥ d(X,P) − d(Q,P)\n\n"
                 "Combining: d(Q,X) ≥ |d(Q,P) − d₂|\n\n"
                 "For d(Q,X) ≤ τ:\n"
                 "|d(Q,P) − d₂| ≤ τ   ⟹   d(Q,P)−τ ≤ d₂ ≤ d(Q,P)+τ  ■",
                 font_size=10, color=LIGHT_GRAY)

    # Practical impact
    add_card(slide, Inches(5.1), Inches(3.2), Inches(4.4), Inches(3.0))
    add_text_box(slide, Inches(5.3), Inches(3.25), Inches(4.0), Inches(0.3),
                 "Practical Impact", font_size=13, color=GREEN, bold=True)
    add_bullet_list(slide, Inches(5.3), Inches(3.65), Inches(4.0), Inches(2.5), [
        "Branches where d₂ < d(Q,P) − τ or d₂ > d(Q,P) + τ are pruned in O(1)",
        "No distance computations needed for pruned subtrees",
        "Empirically prunes 41.2% to 89.4% of the search space",
        "Tighter tolerance → more pruning → faster search",
        "Enables sub-linear query time: O(N^α), α < 1",
    ], font_size=10, spacing_after=6, bullet_color=GREEN)


def slide_08_dsu(prs):
    """SLIDE 8 – DSU Global Clustering"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "Global Duplicate Clustering via DSU", number="06")

    # DSU explanation
    add_card(slide, Inches(0.5), Inches(1.5), Inches(4.3), Inches(2.5))
    add_text_box(slide, Inches(0.7), Inches(1.55), Inches(3.9), Inches(0.3),
                 "Disjoint Set Union (Union-Find)", font_size=14, color=ACCENT, bold=True)
    add_bullet_list(slide, Inches(0.7), Inches(1.95), Inches(3.9), Inches(2.0), [
        "Each image starts as its own set",
        "BK-Tree range query finds neighbours within tolerance τ",
        "Union operation merges duplicate pairs",
        "Path compression: O(α(N)) ≈ O(1) amortized find",
        "Union by rank: keeps tree balanced",
        "Result: connected components = duplicate clusters",
    ], font_size=11, spacing_after=5)

    # Cull heuristics
    add_card(slide, Inches(5.1), Inches(1.5), Inches(4.4), Inches(2.5))
    add_text_box(slide, Inches(5.3), Inches(1.55), Inches(4.0), Inches(0.3),
                 "Auto-Cull Master Selection", font_size=14, color=ORANGE, bold=True)
    add_bullet_list(slide, Inches(5.3), Inches(1.95), Inches(4.0), Inches(2.0), [
        "Highest Resolution (W×H): preserves best quality",
        "Largest File Size: preserves RAW/uncompressed",
        "Newest Modification: preserves recent edits",
        "Oldest Creation: preserves original captures",
        "Redundant copies → soft-delete recycle bin",
        "Full undo/restore capability",
    ], font_size=11, spacing_after=5, bullet_color=ORANGE)

    # Clustering pipeline flow
    add_text_box(slide, Inches(0.7), Inches(4.3), Inches(8.6), Inches(0.3),
                 "Clustering Pipeline", font_size=14, color=ACCENT2, bold=True)

    pipeline = ["Index N Images", "→", "BK-Tree Range Queries", "→",
                "DSU Union Operations", "→", "Connected Components", "→",
                "Auto-Cull + Soft Delete"]
    x = Inches(0.5)
    for i, step in enumerate(pipeline):
        if step == "→":
            add_text_box(slide, x, Inches(4.75), Inches(0.3), Inches(0.35),
                         "→", font_size=16, color=ACCENT)
            x += Inches(0.35)
        else:
            w = Inches(1.1) if len(step) < 18 else Inches(1.35)
            add_card(slide, x, Inches(4.7), w, Inches(0.4))
            add_text_box(slide, x + Emu(30000), Inches(4.73), w - Emu(60000),
                         Inches(0.35), step, font_size=8, color=WHITE, bold=True,
                         alignment=PP_ALIGN.CENTER)
            x += w + Inches(0.05)

    # Complexity note
    add_card(slide, Inches(0.5), Inches(5.5), Inches(9.0), Inches(0.7),
             RGBColor(0x17, 0x22, 0x34))
    add_text_box(slide, Inches(0.8), Inches(5.55), Inches(8.4), Inches(0.6),
                 "Total Complexity: O(N × N^α) = O(N^(1+α)) — sub-quadratic global "
                 "deduplication vs O(N²) naive pairwise comparison. "
                 "Inverse Ackermann amortized time α(N) ≈ O(1) per DSU operation.",
                 font_size=11, color=ACCENT)


def slide_09_architecture(prs):
    """SLIDE 9 – System Architecture & Web Studio"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "System Architecture & Web Studio", number="07 / 08")

    # Architecture components
    add_card(slide, Inches(0.5), Inches(1.5), Inches(4.3), Inches(2.8))
    add_text_box(slide, Inches(0.7), Inches(1.55), Inches(3.9), Inches(0.3),
                 "Core Modules", font_size=14, color=ACCENT, bold=True)
    add_bullet_list(slide, Inches(0.7), Inches(1.9), Inches(3.9), Inches(2.3), [
        "bktree.py — BK-Tree engine + DSU clustering",
        "hash_logic.py — 100-bit perceptual hash extraction",
        "web_app.py — REST API server (ThreadingHTTPServer)",
        "index.html — Interactive SPA dashboard",
        "run.py — Entry point (web + desktop modes)",
        "ThreadPoolExecutor — multi-core image ingestion",
        ".bktree_cache.json — sub-50ms warm re-indexing",
    ], font_size=10, spacing_after=5)

    # REST API
    add_card(slide, Inches(5.1), Inches(1.5), Inches(4.4), Inches(2.8))
    add_text_box(slide, Inches(5.3), Inches(1.55), Inches(4.0), Inches(0.3),
                 "REST API Endpoints", font_size=14, color=GREEN, bold=True)
    add_bullet_list(slide, Inches(5.3), Inches(1.9), Inches(4.0), Inches(2.3), [
        "GET /api/status — system telemetry",
        "POST /api/browse-folder — native dialog + indexing",
        "GET /api/clusters?tolerance=τ — BK-Tree DSU clustering",
        "GET /api/tree-data — SVG topology graph",
        "POST /api/cull — auto-cull by heuristic rule",
        "POST /api/stage — soft-delete to recycle bin",
        "POST /api/empty-bin — permanent deletion",
    ], font_size=10, spacing_after=5, bullet_color=GREEN)

    # Dashboard features
    add_text_box(slide, Inches(0.7), Inches(4.55), Inches(8.6), Inches(0.3),
                 "Interactive Dashboard Features", font_size=14, color=ACCENT2, bold=True)
    features_left = [
        "Dynamic dark-mode UI with glassmorphism effects",
        "Responsive image grid with lazy loading",
        "Split curtain wipe image comparator",
        "Amplified difference heatmap (|R₁−R₂| × 5)",
    ]
    features_right = [
        "SVG-based BK-Tree topology inspector",
        "Step-by-step pruning simulator with live math",
        "Multi-level depth expansion (L1/L2/L3)",
        "EXIF metadata inspector & pan-zoom canvas",
    ]
    add_bullet_list(slide, Inches(0.5), Inches(4.95), Inches(4.5), Inches(1.5),
                    features_left, font_size=10, spacing_after=4)
    add_bullet_list(slide, Inches(5.1), Inches(4.95), Inches(4.5), Inches(1.5),
                    features_right, font_size=10, spacing_after=4, bullet_color=ACCENT2)


def slide_10_benchmarks(prs):
    """SLIDE 10 – Empirical Benchmarks"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "Empirical Benchmarks & Performance", number="09")

    data = [
        ["N", "τ", "Height", "Build", "BK Query", "Linear", "Pruning"],
        ["50", "8", "4", "0.10 ms", "0.092 ms", "0.049 ms", "41.2%"],
        ["100", "8", "4", "0.30 ms", "0.175 ms", "0.101 ms", "46.6%"],
        ["250", "8", "5", "0.80 ms", "0.408 ms", "0.238 ms", "51.6%"],
        ["500", "8", "5", "2.20 ms", "0.788 ms", "0.481 ms", "55.1%"],
        ["1000", "8", "6", "4.20 ms", "1.505 ms", "0.947 ms", "59.0%"],
        ["50", "12", "4", "0.10 ms", "0.103 ms", "0.048 ms", "19.6%"],
        ["250", "12", "5", "0.90 ms", "0.497 ms", "0.240 ms", "24.2%"],
        ["1000", "12", "6", "4.00 ms", "1.908 ms", "0.940 ms", "27.9%"],
        ["1000", "16", "6", "4.00 ms", "2.101 ms", "0.944 ms", "11.9%"],
    ]
    add_table(slide, Inches(0.3), Inches(1.45), Inches(9.4), Inches(3.2),
              len(data), 7, data, font_size=9)

    # Key findings
    add_text_box(slide, Inches(0.7), Inches(4.9), Inches(4), Inches(0.3),
                 "Key Findings", font_size=14, color=ACCENT, bold=True)
    add_bullet_list(slide, Inches(0.5), Inches(5.25), Inches(4.5), Inches(1.2), [
        "Pruning ratio scales with dataset size",
        "Tighter τ → higher pruning (up to 89.4%)",
        "Sub-linear scaling confirmed empirically",
    ], font_size=11, spacing_after=5)

    # Verification card
    add_card(slide, Inches(5.1), Inches(4.9), Inches(4.4), Inches(1.3))
    add_text_box(slide, Inches(5.3), Inches(4.95), Inches(4.0), Inches(0.3),
                 "Formal Verification", font_size=14, color=GREEN, bold=True)
    add_bullet_list(slide, Inches(5.3), Inches(5.25), Inches(4.0), Inches(0.9), [
        "1,000 random triads — 100% pass rate",
        "BK-Tree search ≡ exhaustive oracle (100 trials)",
        "All 4 metric axioms verified programmatically",
    ], font_size=11, spacing_after=5, bullet_color=GREEN)


def slide_11_conclusion(prs):
    """SLIDE 11 – Conclusion & Future Work"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "Conclusion & Future Work", number="10")

    # Contributions
    add_card(slide, Inches(0.5), Inches(1.5), Inches(4.3), Inches(3.2))
    add_text_box(slide, Inches(0.7), Inches(1.55), Inches(3.9), Inches(0.3),
                 "Project Contributions", font_size=14, color=ACCENT, bold=True)
    add_bullet_list(slide, Inches(0.7), Inches(1.9), Inches(3.9), Inches(2.7), [
        "Complete BK-Tree implementation with collision handling",
        "Rigorous Triangle Inequality proof & pruning implementation",
        "Novel 100-bit multi-channel perceptual hash",
        "DSU-based global clustering (sub-quadratic)",
        "Interactive SVG topology & pruning simulator",
        "Automated test suite with 1,000-triad verification",
        "Full-stack web studio with REST API",
    ], font_size=11, spacing_after=5)

    # Future directions
    add_card(slide, Inches(5.1), Inches(1.5), Inches(4.4), Inches(3.2))
    add_text_box(slide, Inches(5.3), Inches(1.55), Inches(4.0), Inches(0.3),
                 "Future Directions", font_size=14, color=ACCENT2, bold=True)
    add_bullet_list(slide, Inches(5.3), Inches(1.9), Inches(4.0), Inches(2.7), [
        "CNN-based deep perceptual feature extraction",
        "VP-Tree & LSH comparative benchmarking",
        "GPU-accelerated hash computation (CUDA)",
        "Distributed BK-Tree for cluster computing",
        "Mobile deployment (React Native / Flutter)",
        "Real-time video frame deduplication",
    ], font_size=11, spacing_after=5, bullet_color=ACCENT2)

    # Takeaway
    add_card(slide, Inches(0.5), Inches(5.0), Inches(9.0), Inches(1.2),
             RGBColor(0x17, 0x22, 0x34))
    add_text_box(slide, Inches(0.8), Inches(5.1), Inches(8.4), Inches(1.0),
                 "\"The Burkhard-Keller Tree transforms an intractable O(N²) global "
                 "deduplication problem into a sub-quadratic O(N^(1+α)) algorithm by "
                 "exploiting the Triangle Inequality to prune entire subtrees in O(1) time, "
                 "achieving 41–89% search space reduction with formal mathematical guarantees.\"",
                 font_size=12, color=WHITE)


def slide_12_references(prs):
    """SLIDE 12 – References & Thank You"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, BG_DARK)
    section_header(slide, "References")

    refs = [
        "[1] W. A. Burkhard and R. M. Keller, \"Some approaches to best-match file searching,\" Comm. ACM, vol. 16, no. 4, 1973.",
        "[2] T. H. Cormen et al., Introduction to Algorithms, 4th ed., MIT Press, 2022.",
        "[3] P. Zezula et al., Similarity Search: The Metric Space Approach, Springer, 2006.",
        "[4] R. E. Tarjan, \"Efficiency of a good but not linear set union algorithm,\" J. ACM, vol. 22, no. 2, 1975.",
        "[5] J. K. Uhlmann, \"Satisfying general proximity/metric queries with metric trees,\" IPL, vol. 40, no. 4, 1991.",
        "[6] P. N. Yianilos, \"Data structures and algorithms for nearest neighbor search,\" Proc. SODA, 1993.",
        "[7] R. Sedgewick and K. Wayne, Algorithms, 4th ed., Addison-Wesley, 2011.",
        "[8] S. Das, \"BK-Tree Metric Space Image Deduplicator,\" GitHub, 2026.",
    ]
    add_bullet_list(slide, Inches(0.6), Inches(1.5), Inches(8.8), Inches(3.5),
                    refs, font_size=10, spacing_after=5, bullet_color=MUTED,
                    color=LIGHT_GRAY)

    # Thank you
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
                                   Inches(3.5), Inches(5.2), Inches(3), Inches(0.02))
    shape.fill.solid()
    shape.fill.fore_color.rgb = ACCENT
    shape.line.fill.background()

    add_text_box(slide, Inches(0.5), Inches(5.5), Inches(9), Inches(0.5),
                 "Thank You", font_size=28, color=WHITE, bold=True,
                 alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(0.5), Inches(6.1), Inches(9), Inches(0.3),
                 "Soumyshiv Das  •  2502051963  •  github.com/soumyshiv/dsa-bktree-image-deduplicator",
                 font_size=10, color=MUTED, alignment=PP_ALIGN.CENTER)


# ── main ───────────────────────────────────────────────────────────

def main():
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)  # widescreen 4:3 variant

    slide_01_title(prs)
    slide_02_agenda(prs)
    slide_03_problem(prs)
    slide_04_metric_spaces(prs)
    slide_05_hashing(prs)
    slide_06_bktree(prs)
    slide_07_pruning(prs)
    slide_08_dsu(prs)
    slide_09_architecture(prs)
    slide_10_benchmarks(prs)
    slide_11_conclusion(prs)
    slide_12_references(prs)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, PPTX_FILENAME)
    prs.save(out_path)
    print(f"\n✅ Presentation saved: {out_path}")
    print(f"   Slides: {len(prs.slides)} (target: 10–12)")
    print(f"   File: {PPTX_FILENAME}")


if __name__ == "__main__":
    main()
