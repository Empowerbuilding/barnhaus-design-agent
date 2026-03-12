"""Auto-generated Revit patch from enhance_diff — eda1a47f"""
import sys
sys.path.insert(0, '/home/mitch/.openclaw/workspace')
from barnhaus_revit_utils import place_window

LEVEL = 'Level 1.0'
WIN   = 'Instance-Window-Fixed'

print('=== Applying enhance diff patch ===')

# [0] Large window — LW south (master bed front face), centered on wall (x=0→22, center=11)
place_window(5953192,  5, 8, 1.0, WIN, '48" x 96"', label='DIFF-LW-S-0')
place_window(5953192, 15, 8, 1.0, WIN, '48" x 96"', label='DIFF-LW-S-1')

# [1] Large window — RW south (bedroom wing front face), centered (x=84→106)
place_window(5953214,  89, 8, 1.0, WIN, '48" x 96"', label='DIFF-RW-S-0')
place_window(5953214, 100, 8, 1.0, WIN, '48" x 96"', label='DIFF-RW-S-1')

# [2] CB south — flanking the front entry door (door at x=53)
place_window(5953203, 44, 26, 1.0, WIN, '48" x 96"', label='DIFF-CB-S-0')
place_window(5953203, 62, 26, 1.0, WIN, '48" x 96"', label='DIFF-CB-S-1')

print('=== Patch complete ===')
