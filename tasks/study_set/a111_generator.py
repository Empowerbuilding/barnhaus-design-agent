"""
a111_generator.py — Generates the A111 upsell page PDF for study sets.

Produces a clean 24x36 sheet matching Barnhaus style:
  - Dark header with project name
  - "Upgrade to the Full Construction Set" pitch
  - What's included in the full set (bullet list)
  - Voucher code callout box
  - Barnhaus branding footer
"""

from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Barnhaus brand colors
BRAND_GOLD   = colors.HexColor("#B8860B")
BRAND_BLACK  = colors.HexColor("#1A1A1A")
BRAND_OFFWHITE = colors.HexColor("#F5F5F0")
BRAND_GRAY   = colors.HexColor("#4A4A4A")
LIGHT_GOLD   = colors.HexColor("#F5E6C8")

# Page size: Arch D 24x36 landscape (Revit standard)
PAGE_W = 36 * inch
PAGE_H = 24 * inch


FULL_SET_CONTENTS = [
    ("19 Sheets of Construction Documents", "Everything a builder needs to break ground"),
    ("Dimension Plans (F1 & F2)", "All wall-to-wall dimensions, openings, and room locations"),
    ("Ceiling Plans", "Height callouts, vault locations, ceiling fan positions"),
    ("Steel Cross Sections", "I-beam sizing references and floor height relationships"),
    ("Roof Layout Plan", "Roof slopes, overhangs, skylight locations, I-beam positions"),
    ("Column Placement Plan", "Steel column grid with heights and beam specs"),
    ("Interior Elevations", "Kitchen, bathrooms, bar, fireplace — 14 views"),
    ("Electrical Plan (F1 & F2)", "Full lighting layout, outlets, switches, panel locations"),
    ("Foundation Plan", "Slab steps, weld plate notes, J-hook callouts"),
    ("Plumbing Plan (F1 & F2)", "All fixture locations, gas lines, hose bibs, chase locations"),
]


def generate_a111(project_name: str, full_sheet_count: int,
                  output_path: str, voucher_code: str = None):
    """
    Generate the A111 upsell page.

    Args:
        project_name:     e.g. "Spring Mountain Construction Set"
        full_sheet_count: Number of sheets in the full set (shown in pitch)
        output_path:      Where to write the PDF
        voucher_code:     Optional promo code (auto-generated if None)
    """
    if voucher_code is None:
        # Auto-generate from project name: "SPRING-MOUNTAIN-VIP"
        slug = project_name.upper().replace(" ", "-").replace("_", "-")
        # Strip common suffixes
        for suffix in ["-CONSTRUCTION-SET", "-STUDY-SET", "-FULL-SET"]:
            slug = slug.replace(suffix, "")
        voucher_code = f"{slug}-VIP"

    c = rl_canvas.Canvas(output_path, pagesize=(PAGE_W, PAGE_H))

    _draw_background(c)
    _draw_header(c, project_name)
    _draw_hero_text(c)
    _draw_what_you_get(c, full_sheet_count)
    _draw_voucher(c, voucher_code)
    _draw_footer(c)
    _draw_title_block(c, project_name)

    c.save()


# ─────────────────────────────────────────────────────────────────────────────
# DRAWING SECTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _draw_background(c):
    c.setFillColor(BRAND_OFFWHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def _draw_header(c, project_name: str):
    """Dark gold header bar with project name."""
    header_h = 3.2 * inch
    y_top = PAGE_H - header_h

    # Background
    c.setFillColor(BRAND_BLACK)
    c.rect(0, y_top, PAGE_W, header_h, fill=1, stroke=0)

    # Gold accent line at bottom of header
    c.setFillColor(BRAND_GOLD)
    c.rect(0, y_top, PAGE_W, 0.08 * inch, fill=1, stroke=0)

    # Company name
    c.setFillColor(BRAND_GOLD)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 1.1 * inch, "BARNHAUS STEEL BUILDERS")

    # Project name
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 16)
    # Truncate long project names
    display_name = project_name.replace(" Construction Set", "").replace(" Study Set", "")
    c.drawCentredString(PAGE_W / 2, PAGE_H - 1.7 * inch, display_name.upper())

    # Tagline
    c.setFillColor(BRAND_GOLD)
    c.setFont("Helvetica-Oblique", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 2.4 * inch, "Custom Steel Frame Homes  ·  Canyon Lake, TX")


def _draw_hero_text(c):
    """Big CTA headline."""
    y = PAGE_H - 4.4 * inch

    c.setFillColor(BRAND_BLACK)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(PAGE_W / 2, y, "READY TO BREAK GROUND?")

    y -= 0.55 * inch
    c.setFillColor(BRAND_GOLD)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(PAGE_W / 2, y, "UPGRADE TO THE FULL CONSTRUCTION SET")

    y -= 0.6 * inch
    c.setFillColor(BRAND_GRAY)
    c.setFont("Helvetica", 15)
    c.drawCentredString(PAGE_W / 2, y,
        "This study set gives you the layout and aesthetics. The full set gives your builder everything to build it.")


def _draw_what_you_get(c, full_sheet_count: int):
    """Two-column list of what's in the full set."""
    section_title_y = PAGE_H - 7.0 * inch

    # Section header
    c.setFillColor(BRAND_BLACK)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(PAGE_W / 2, section_title_y,
        f"THE FULL CONSTRUCTION SET INCLUDES {full_sheet_count} SHEETS:")

    # Gold underline
    c.setStrokeColor(BRAND_GOLD)
    c.setLineWidth(2)
    underline_w = 8 * inch
    c.line(PAGE_W/2 - underline_w/2, section_title_y - 0.12*inch,
           PAGE_W/2 + underline_w/2, section_title_y - 0.12*inch)

    # Two-column layout
    col1_x = 1.5 * inch
    col2_x = PAGE_W / 2 + 0.5 * inch
    row_h  = 0.75 * inch
    start_y = section_title_y - 0.55 * inch

    for i, (title, desc) in enumerate(FULL_SET_CONTENTS):
        col_x = col1_x if i % 2 == 0 else col2_x
        row_y = start_y - (i // 2) * row_h

        # Gold bullet
        c.setFillColor(BRAND_GOLD)
        c.circle(col_x - 0.15 * inch, row_y + 0.08 * inch, 0.05 * inch, fill=1, stroke=0)

        # Title
        c.setFillColor(BRAND_BLACK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(col_x, row_y + 0.04 * inch, title)

        # Description
        c.setFillColor(BRAND_GRAY)
        c.setFont("Helvetica", 10)
        c.drawString(col_x, row_y - 0.22 * inch, desc)


def _draw_voucher(c, voucher_code: str):
    """Prominent voucher code box."""
    box_w  = 14 * inch
    box_h  = 2.2 * inch
    box_x  = (PAGE_W - box_w) / 2
    box_y  = 1.9 * inch

    # Box background
    c.setFillColor(BRAND_GOLD)
    c.roundRect(box_x, box_y, box_w, box_h, 0.15 * inch, fill=1, stroke=0)

    # Inner dark box
    pad = 0.12 * inch
    c.setFillColor(BRAND_BLACK)
    c.roundRect(box_x + pad, box_y + pad, box_w - 2*pad, box_h - 2*pad,
                0.1 * inch, fill=1, stroke=0)

    # "$100 OFF" text
    c.setFillColor(BRAND_GOLD)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(PAGE_W / 2, box_y + box_h - 0.65 * inch, "SAVE $100 INSTANTLY")

    # Voucher label
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 13)
    c.drawCentredString(PAGE_W / 2, box_y + 0.72 * inch, "USE CODE AT CHECKOUT:")

    # Code itself
    c.setFillColor(BRAND_GOLD)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(PAGE_W / 2, box_y + 0.22 * inch, voucher_code)


def _draw_footer(c):
    """Footer with contact info."""
    y = 0.8 * inch
    c.setFillColor(BRAND_GRAY)
    c.setFont("Helvetica", 11)
    c.drawCentredString(PAGE_W / 2, y,
        "barnhaussteelbuilders.com  ·  210-517-7267  ·  Canyon Lake, TX")

    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.HexColor("#888888"))
    c.drawCentredString(PAGE_W / 2, y - 0.25 * inch,
        "Barnhaus Steel Builders does not engineer or certify plans. "
        "Engineered foundation and structural drawings required prior to construction.")


def _draw_title_block(c, project_name: str):
    """Minimal title block in bottom-right corner (matches Revit sheet style)."""
    block_w = 3.5 * inch
    block_h = 1.2 * inch
    block_x = PAGE_W - block_w - 0.15 * inch
    block_y = 0.15 * inch

    c.setStrokeColor(BRAND_BLACK)
    c.setLineWidth(0.5)
    c.rect(block_x, block_y, block_w, block_h, fill=0, stroke=1)

    c.setFillColor(BRAND_BLACK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(block_x + 0.1*inch, block_y + 0.85*inch, "BARNHAUS STEEL BUILDERS")

    c.setFont("Helvetica", 8)
    short_name = project_name.replace(" Construction Set", "").replace(" Study Set", "")
    c.drawString(block_x + 0.1*inch, block_y + 0.6*inch, short_name)

    c.setFont("Helvetica", 8)
    c.drawString(block_x + 0.1*inch, block_y + 0.38*inch, "Sheet: A111")
    c.drawString(block_x + 1.5*inch, block_y + 0.38*inch, "Scale: N/A")

    import time
    c.drawString(block_x + 0.1*inch, block_y + 0.18*inch,
                 f"Date: {time.strftime('%m/%d/%Y')}")
    c.drawString(block_x + 1.5*inch, block_y + 0.18*inch, "Arch D 24\"x36\"")
