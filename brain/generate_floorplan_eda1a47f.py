#!/usr/bin/env python3
"""Generate 2D floor plan image for eda1a47f H-shape Barnhaus design."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np

ID = "eda1a47f"

# ─── ZONE COLORS ───────────────────────────────────────────────
COLORS = {
    "master":   "#D4A5A5",   # dusty rose
    "kitchen":  "#A5C4D4",   # steel blue
    "great_rm": "#A5D4B8",   # sage green
    "bed":      "#D4C4A5",   # warm tan
    "bath":     "#B8A5D4",   # lavender
    "service":  "#D4D4A5",   # warm yellow
    "garage":   "#C0C0C0",   # grey
    "porch":    "#F0E6C8",   # cream
    "hall":     "#E8E8E8",   # light grey
    "closet":   "#D4B8A5",   # warm brown
    "pantry":   "#A5D4C4",   # teal-light
}

fig, ax = plt.subplots(1, 1, figsize=(20, 16))
ax.set_aspect('equal')
ax.set_facecolor('#F5F5F0')
fig.patch.set_facecolor('#F5F5F0')

def room(ax, x0, y0, x1, y1, label, sf, color, fontsize=8):
    w, h = x1 - x0, y1 - y0
    rect = mpatches.FancyBboxPatch((x0, y0), w, h,
                                    boxstyle="square,pad=0",
                                    facecolor=color, edgecolor='#333333',
                                    linewidth=1.2)
    ax.add_patch(rect)
    cx, cy = (x0+x1)/2, (y0+y1)/2
    ax.text(cx, cy+0.5, label, ha='center', va='center',
            fontsize=fontsize, fontweight='bold', color='#1a1a1a')
    if sf:
        ax.text(cx, cy-0.8, f"{sf} SF", ha='center', va='center',
                fontsize=6.5, color='#444444')

def outline(ax, pts, color='#222222', lw=2.5):
    xs = [p[0] for p in pts] + [pts[0][0]]
    ys = [p[1] for p in pts] + [pts[0][1]]
    ax.plot(xs, ys, color=color, linewidth=lw)

# ─── COORDINATE SYSTEM ────────────────────────────────────────
# y=0 = REAR/VIEW (north, back porch side)
# y increases = FRONT/STREET (south)
# x=0 = WEST, x increases = EAST

# ─── H-SHAPE ZONES ────────────────────────────────────────────
# Left Wing:     x=0-22,  y=8-54
# Left BZ:       x=22-28, y=16-44
# Center Bridge: x=28-58, y=16-44
# Right BZ:      x=58-64, y=16-44
# Right Wing:    x=64-86, y=8-54
# Back Porch:    x=28-58, y=4-16
# Front Porch:   x=37-49, y=44-56
# Garage:        x=0-36,  y=54-78

# ─── DRAW ZONE BACKGROUNDS ────────────────────────────────────
# Left Wing background
bg_lw = mpatches.Rectangle((0, 8), 22, 46, facecolor='#FAF6F0', edgecolor='#333', linewidth=2)
ax.add_patch(bg_lw)
# Center Bridge background
bg_cb = mpatches.Rectangle((22, 16), 64-22, 28, facecolor='#F0FAF4', edgecolor='#333', linewidth=2)
ax.add_patch(bg_cb)
# Right Wing background
bg_rw = mpatches.Rectangle((64, 8), 22, 46, facecolor='#FAF6F0', edgecolor='#333', linewidth=2)
ax.add_patch(bg_rw)

# ─── BACK PORCH (rear/north = small y) ────────────────────────
room(ax, 28, 4, 58, 16, "BACK PORCH\n(Covered, Cedar T&G)", 360, COLORS['porch'], fontsize=8)
# Porch posts indicated by dots
for px in [29.5, 45, 56.5]:
    ax.plot(px, 4.5, 'ko', markersize=6)
ax.text(45, 4.0, "▲ REAR / VIEW", ha='center', va='top', fontsize=8, color='#444', style='italic')

# ─── FRONT PORCH (street/south = large y) ─────────────────────
room(ax, 37, 44, 49, 56, "FRONT\nPORCH", 144, COLORS['porch'], fontsize=7)
for px in [38, 48]:
    ax.plot(px, 55.5, 'ko', markersize=6)

# ─── LEFT WING ROOMS ──────────────────────────────────────────
# Master Bedroom
room(ax, 0, 8, 22, 22, "MASTER BEDROOM", 308, COLORS['master'])
# Rear slider on master (y=8 wall)
ax.annotate("", xy=(8, 8), xytext=(14, 8),
            arrowprops=dict(arrowstyle="<->", color='blue', lw=1.5))
ax.text(11, 7.0, "6ft Slider →Patio", ha='center', fontsize=6, color='blue')

# Master Bath
room(ax, 0, 22, 14, 32, "MASTER BATH", 140, COLORS['bath'])
ax.text(7, 25, "🚿 Shower\n🛁 Tub\n🪥 Dbl Vanity", ha='center', va='center',
        fontsize=5.5, color='#333')

# WIC
room(ax, 14, 22, 22, 32, "W.I.C.", 80, COLORS['closet'])

# Butler Pantry
room(ax, 0, 32, 8, 44, "BUTLER\nPANTRY", 96, COLORS['pantry'])

# Kitchen
room(ax, 8, 32, 22, 44, "KITCHEN", 168, COLORS['kitchen'])
ax.text(15, 37, "Island →", ha='center', fontsize=6, color='#555')

# Laundry
room(ax, 0, 44, 11, 54, "LAUNDRY", 110, COLORS['service'])

# Utility / Mudroom
room(ax, 11, 44, 22, 54, "UTILITY /\nMUDROOM", 110, COLORS['service'])

# ─── OPEN PLAN CENTER (CB + Breezeways) ───────────────────────
# Dining (open to kitchen and great room)
room(ax, 22, 16, 42, 30, "DINING", 190, COLORS['kitchen'], fontsize=8)

# Great Room
room(ax, 28, 30, 58, 44, "GREAT ROOM", 420, COLORS['great_rm'], fontsize=10)
ax.text(43, 37, "16 ft VAULTED CEILING", ha='center', fontsize=7,
        color='#1a6b3a', fontweight='bold')
# Rear slider great room
ax.annotate("", xy=(36, 16), xytext=(50, 16),
            arrowprops=dict(arrowstyle="<->", color='blue', lw=1.5))
ax.text(43, 15.2, "12ft Multi-Panel Slider", ha='center', fontsize=6, color='blue')

# Hero volume label
ax.text(43, 31.5, "HERO SPACE", ha='center', fontsize=7.5,
        color='#2a6a3a', style='italic')

# Left breezeway (open hall)
room(ax, 22, 30, 28, 44, "HALL", None, COLORS['hall'], fontsize=7)

# Right breezeway (open hall)
room(ax, 58, 16, 64, 44, "HALL", None, COLORS['hall'], fontsize=7)

# ─── RIGHT WING ROOMS ─────────────────────────────────────────
# Bed 2
room(ax, 64, 8, 78, 24, "BED 2", 224, COLORS['bed'])
# Bath 2
room(ax, 78, 8, 86, 22, "BATH 2", 112, COLORS['bath'])
# RW Hallway
room(ax, 64, 22, 86, 26, "HALLWAY", 88, COLORS['hall'], fontsize=7)
# Bed 3
room(ax, 64, 26, 78, 42, "BED 3", 224, COLORS['bed'])
# Bath 3
room(ax, 78, 26, 86, 42, "BATH 3", 128, COLORS['bath'])
# South storage / flex
room(ax, 64, 42, 86, 54, "LINEN /\nSTORAGE", 264, COLORS['hall'], fontsize=7)

# Front entry door on RW (y=54 south face)
ax.annotate("", xy=(73, 54), xytext=(77, 54),
            arrowprops=dict(arrowstyle="<->", color='green', lw=1.5))
ax.text(75, 54.8, "Entry Door", ha='center', fontsize=6, color='green')

# ─── GARAGE ───────────────────────────────────────────────────
room(ax, 0, 54, 36, 78, "3-CAR GARAGE\n(Side Loaded)", 864, COLORS['garage'], fontsize=9)
# Garage doors on south face (y=78)
for gx in [5.5, 17.5, 29.5]:
    rect = mpatches.Rectangle((gx, 77.0), 9, 1.5,
                                facecolor='#aaaaaa', edgecolor='#333', linewidth=1)
    ax.add_patch(rect)
ax.text(18, 75.5, "← 3 × 10ft Overhead Doors →", ha='center', fontsize=7, color='#333')

# Mudroom connection note
ax.annotate("", xy=(18, 54), xytext=(18, 58),
            arrowprops=dict(arrowstyle="->", color='green', lw=1.5))
ax.text(19, 56, "→Mudroom", ha='left', fontsize=6.5, color='green')

# ─── ZONE HEIGHT ANNOTATIONS ──────────────────────────────────
ax.text(11, 8.5, "10 ft WALLS", ha='center', fontsize=6.5,
        color='#6b3a1a', style='italic')
ax.text(43, 16.5, "16 ft VAULTED CENTER BRIDGE", ha='center', fontsize=7,
        color='#1a6b3a', fontweight='bold')
ax.text(75, 8.5, "10 ft WALLS", ha='center', fontsize=6.5,
        color='#6b3a1a', style='italic')

# ─── EXTERIOR OUTLINE ─────────────────────────────────────────
# H-shape outline
h_pts = [
    (0,8), (22,8), (22,16), (28,16), (28,4), (58,4), (58,16), (64,16),
    (64,8), (86,8), (86,54), (64,54), (64,44), (58,44), (58,44),
    (49,44), (49,56), (37,56), (37,44), (28,44), (28,44),
    (22,44), (22,54), (0,54), (0,8)
]
outline(ax, h_pts, '#222222', 2.5)
# Garage outline
g_pts = [(0,54),(36,54),(36,78),(0,78),(0,54)]
outline(ax, g_pts, '#555555', 2)

# ─── NORTH ARROW ──────────────────────────────────────────────
ax.annotate("N", xy=(92, 10), xytext=(92, 6),
            fontsize=10, ha='center', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='black', lw=2))
ax.text(92, 5.0, "↑ REAR/VIEW", ha='center', fontsize=7)
ax.text(92, 58.5, "↓ STREET", ha='center', fontsize=7)

# ─── DIMENSIONS ───────────────────────────────────────────────
ax.annotate("", xy=(86, 3), xytext=(0, 3),
            arrowprops=dict(arrowstyle="<->", color='#444', lw=1))
ax.text(43, 2.3, "86 ft total width", ha='center', fontsize=8, color='#444')

ax.annotate("", xy=(89, 8), xytext=(89, 54),
            arrowprops=dict(arrowstyle="<->", color='#444', lw=1))
ax.text(90.5, 31, "46 ft\ndepth", ha='left', fontsize=8, color='#444')

ax.annotate("", xy=(-3, 54), xytext=(-3, 78),
            arrowprops=dict(arrowstyle="<->", color='#666', lw=1))
ax.text(-4.5, 66, "24 ft\ngarage", ha='right', fontsize=7, color='#666')

# ─── TITLE BLOCK ──────────────────────────────────────────────
ax.text(43, 83, "BARNHAUS STEEL BUILDERS", ha='center', fontsize=14,
        fontweight='bold', color='#1a1a1a')
ax.text(43, 81, "Design Submission: eda1a47f — Mitchell Madison | 3,200 SF Living | H-Shape", 
        ha='center', fontsize=9, color='#444')
ax.text(43, 79.5, "Style: Hill Country | 3 Bed / 3 Bath (Ensuite) | 3-Car Side-Loaded Garage | 16ft Vaulted Great Room",
        ha='center', fontsize=8, color='#666')

# ─── LEGEND ───────────────────────────────────────────────────
legend_items = [
    (COLORS['master'],  "Master Suite"),
    (COLORS['kitchen'], "Kitchen / Dining"),
    (COLORS['great_rm'],"Great Room"),
    (COLORS['bed'],     "Secondary Bedrooms"),
    (COLORS['bath'],    "Bathrooms"),
    (COLORS['pantry'],  "Butler Pantry"),
    (COLORS['service'], "Laundry / Service"),
    (COLORS['garage'],  "Garage"),
    (COLORS['porch'],   "Covered Porch"),
    (COLORS['hall'],    "Hallway / Storage"),
]
for i, (c, lbl) in enumerate(legend_items):
    bx = 0 + (i % 5) * 17.5
    by = 85.5 + (i // 5) * 2.0
    ax.add_patch(mpatches.Rectangle((bx, by), 3, 1.4, facecolor=c, edgecolor='#555', linewidth=0.8))
    ax.text(bx + 3.5, by + 0.7, lbl, va='center', fontsize=7.5)

# ─── FINALIZE ─────────────────────────────────────────────────
ax.set_xlim(-8, 100)
ax.set_ylim(-2, 92)
ax.axis('off')
plt.tight_layout()

out_path = f"/home/mitch/.openclaw/workspace/designs/floorplan_{ID}.png"
plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='#F5F5F0')
print(f"✅ Floor plan saved: {out_path}")
plt.close()
