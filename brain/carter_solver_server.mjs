/**
 * Carter AI Solver Server
 * Sits between the canvas and Anthropic API.
 * POST /solve  → takes bubble positions, returns AI-derived box layout
 * GET  /health → simple ping
 */

import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { readFileSync } from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load .env
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
  readFileSync(envPath, 'utf8').split('\n').forEach(line => {
    const [k, ...v] = line.split('=');
    if (k && v.length) process.env[k.trim()] = v.join('=').trim().replace(/^"|"$/g, '');
  });
}

const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY;
const OPENAI_KEY = process.env.OPENAI_API_KEY;
const PORT = 3747;

// ─── V4 Reference Box Positions (ground truth) ───────────────────────────────
const V4_BOXES = {
  // ── Master Wing (S1–S2) ──────────────────────────────────────────────────
  his_closet:   { x:100, y:390, w:80,  h:55  },
  // M. Bath fills gap below His Closet all the way to Hers Closet — no void
  m_bath:       { x:100, y:445, w:120, h:168 },
  // Hers Closet bumped down slightly below M. Bath
  hers_closet:  { x:100, y:618, w:100, h:68  },
  master_bed:   { x:180, y:390, w:165, h:223 },

  // ── Bed Wing (S2–S3) above Hallway 1 ────────────────────────────────────
  // Bath 2: portrait rectangle — narrower E-W (5-6ft), taller N-S (8-9ft)
  // Narrower width frees up more room for Bed 2 → squarer Bed 2
  bath2:        { x:340, y:458, w:64,  h:80  },
  // WIC 2: fills column below Bath 2, roughly square
  wic2:         { x:340, y:538, w:64,  h:40  },
  // Bed 2: now wider and near-square
  bed2:         { x:404, y:458, w:116, h:120 },

  // ── Bed Wing below Hallway 1 ─────────────────────────────────────────────
  bed1:         { x:200, y:613, w:140, h:105 },
  wic1:         { x:340, y:613, w:80,  h:43  },
  half_bath:    { x:420, y:613, w:100, h:43  },
  // Bath 1: stretches FULL WIDTH from S2(340) to S3(520), shallow N-S
  // Creates a clean wide bottom edge — nice bump-out for Bed 1
  bath1:        { x:340, y:658, w:180, h:60  },

  // ── Great Room (S3–S4) ───────────────────────────────────────────────────
  great_room:   { x:520, y:370, w:360, h:440 },
  // Office is a sub-room INSIDE the Great Room, front/bottom zone
  office:       { x:525, y:700, w:130, h:110 },

  // ── Service Spine (S4–S5) ────────────────────────────────────────────────
  hallway2:     { x:875, y:420, w:90,  h:55  },
  pantry:       { x:875, y:475, w:100, h:135 },
  mech:         { x:875, y:610, w:90,  h:130 },

  // ── Garage Wing (S5–S6) ──────────────────────────────────────────────────
  mud_room:     { x:980, y:390, w:140, h:90  },
  garage:       { x:980, y:480, w:260, h:380 },
};

// ─── Architectural Rules ──────────────────────────────────────────────────────
const ARCH_RULES = `
You are an expert architectural layout engine. Your job is to adjust box positions based on where the user moved their bubbles, while respecting hard architectural rules.

CANVAS: 1300 wide x 920 tall. No rooms above y=80.

SECTION LINES — S1=100, S2=340, S3=520, S4=880, S5=980, S6=1240
SECTION LINES ARE SOFT GUIDES ONLY. Only snap a room edge to a section line if that edge is already within 30px of it. Do NOT pull rooms across the canvas to reach a section line. Sections define zone boundaries, not magnets.

ZONES (rooms belong in their zone unless a bubble explicitly crossed into another):
- Master Wing  (x 100–340): master_bed, m_bath, his_closet, hers_closet
- Bed Wing     (x 340–520): bed1, bed2, bath1, bath2, wic1, wic2, half_bath
- Great Room   (x 520–880): great_room, office (office is INSIDE great_room, not exterior)
- Service      (x 880–980): hallway2, pantry, mech
- Garage       (x 980–1240): mud_room, garage

HALLWAY 1: Always render as a horizontal corridor at approximately y=578–613, spanning x=220–520. It separates the master wing (top) from bed1/bath1 zone (bottom). It is NOT a draggable bubble — always include it in output at these fixed coordinates.

HARD RULES:
1. STAY CLOSE TO BUBBLE POSITIONS. The bubble center is the user's intent. Your box center should not drift more than 80px from the bubble center unless a hard rule forces it.
2. Bedrooms (bed1, bed2, master_bed) must be NEAR-SQUARE. Max aspect ratio 1.6:1. Never make a bedroom a long skinny rectangle.
3. Bedrooms get exterior wall — at least one face must touch the perimeter of their zone.
4. Bathrooms and closets are INTERIOR — they sit beside/below their bedroom, not on the outer perimeter.
5. Master Bath is LEFT of Master Bed (lower x), extends below it.
6. Hers Closet is BELOW Master Bath.
7. Bath1 is directly below or beside Bed1, sharing a wall.
8. WIC1 is between Bed1 and Bath1 (small room).
9. Office is a sub-room inside the Great Room envelope — it sits at the bottom/front of the great room zone, not outside it.
10. Service rooms (pantry, mech, hallway2) stay compact — their widths should not exceed 100px.
11. Garage extends downward — its bottom edge should be around y=860.
12. Mud Room is compact (w≈140, h≈90), sits above the garage.
13. No overlapping rooms. If boxes would collide, shrink the smaller room, never the bedroom.
14. Use the V4 reference positions below as your anchor — only move a room proportionally to how far its bubble moved from its default position.
15. M. BATH fills the entire vertical space from below His Closet (y≈445) down to Hers Closet — no gap or void.
16. BATH 2 is a portrait rectangle: ~64px wide × ~80px tall. Occupies the LEFT column of Zone 1 at x=340. Narrower width frees space so Bed 2 can be near-square.
17. WIC 2 fills the column below Bath 2, same width (~64px), approximately square.
18. BED 2 takes the right portion of Zone 1 starting at x≈404. Must be near-square (max 1.6:1 ratio).
19. BATH 1 stretches the FULL WIDTH from S2(x=340) to S3(x=520) — w=180px, shallow h≈60px. Wide shallow rectangle along the bottom edge of the bedroom wing. Creates a clean bump-out for Bed 1 above it.
20. No room may have aspect ratio worse than 2.5:1. Bedrooms max 1.6:1.

V4 REFERENCE BOX POSITIONS (use as baseline, adjust proportionally to bubble movement):
`;

// ─── Call Claude ──────────────────────────────────────────────────────────────
async function callClaude(bubbles, sections) {
  // Build default bubble positions for delta calculation
  const DEFAULT_BUBBLES = {
    master_bed:  { cx:262, cy:484 }, m_bath:     { cx:160, cy:556 },
    his_closet:  { cx:140, cy:417 }, hers_closet:{ cx:150, cy:650 },
    bed2:        { cx:470, cy:518 }, bath2:       { cx:380, cy:498 },
    wic2:        { cx:380, cy:558 }, bed1:        { cx:270, cy:678 },
    wic1:        { cx:380, cy:634 }, half_bath:   { cx:470, cy:634 },
    bath1:       { cx:380, cy:699 }, great_room:  { cx:700, cy:590 },
    office:      { cx:590, cy:755 }, pantry:      { cx:925, cy:542 },
    mech:        { cx:920, cy:675 }, hallway2:    { cx:920, cy:447 },
    mud_room:    { cx:1050,cy:435 }, garage:      { cx:1110,cy:670 },
  };

  // Calculate deltas
  const deltas = bubbles.map(b => {
    const def = DEFAULT_BUBBLES[b.id];
    return def ? { id: b.id, dx: b.cx - def.cx, dy: b.cy - def.cy } : { id: b.id, dx: 0, dy: 0 };
  });

  const prompt = `${ARCH_RULES}
${JSON.stringify(V4_BOXES, null, 2)}

BUBBLE MOVEMENT DELTAS (how far each bubble moved from its default position):
${JSON.stringify(deltas, null, 2)}

CURRENT BUBBLE POSITIONS:
${JSON.stringify(bubbles.map(b => ({ id: b.id, label: b.label, cx: b.cx, cy: b.cy, r: b.r })), null, 2)}

TASK:
1. Start from the V4 reference positions above.
2. For each room, shift its box by approximately the same delta as its bubble moved (dx, dy).
3. Apply all hard rules to clean up any violations.
4. Always include "hallway1" as { "id": "hallway1", "x": 220, "y": 578, "w": 300, "h": 35 } — it is always there.
5. Return ONLY a valid JSON array. Each entry: { "id": "<room_id>", "x": <int>, "y": <int>, "w": <int>, "h": <int> }
No markdown, no explanation, just the JSON array.`;

  // Use OpenAI if available, fall back to Anthropic
  let text;
  if (OPENAI_KEY) {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OPENAI_KEY}`,
      },
      body: JSON.stringify({
        model: 'gpt-4o',
        max_tokens: 2048,
        messages: [{ role: 'user', content: prompt }],
      }),
    });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(`OpenAI API error ${response.status}: ${err}`);
    }
    const data = await response.json();
    text = data.choices?.[0]?.message?.content || '';
  } else {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-5',
        max_tokens: 2048,
        messages: [{ role: 'user', content: prompt }],
      }),
    });
    if (!response.ok) {
      const err = await response.text();
      throw new Error(`Anthropic API error ${response.status}: ${err}`);
    }
    const data = await response.json();
    text = data.content?.[0]?.text || '';
  }

  // Parse JSON from response (strip any accidental markdown)
  const cleaned = text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
  return JSON.parse(cleaned);
}

// ─── HTTP Server ──────────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }

  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', model: 'claude-sonnet-4-5' }));
    return;
  }

  if (req.method === 'POST' && req.url === '/solve') {
    let body = '';
    req.on('data', d => body += d);
    req.on('end', async () => {
      try {
        const { bubbles, sections } = JSON.parse(body);
        console.log(`[solver] Solving layout for ${bubbles.length} rooms...`);

        const boxes = await callClaude(bubbles, sections);
        console.log(`[solver] Got ${boxes.length} boxes back from Claude`);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, boxes }));
      } catch (err) {
        console.error('[solver] Error:', err.message);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: err.message }));
      }
    });
    return;
  }

  res.writeHead(404); res.end('Not found');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`🦞 Carter AI Solver running at http://localhost:${PORT}`);
  console.log(`   POST /solve  — AI layout from bubbles`);
  console.log(`   GET  /health — ping`);
  if (!ANTHROPIC_KEY) console.warn('⚠️  ANTHROPIC_API_KEY not found in .env!');
});
