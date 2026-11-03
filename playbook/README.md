# Playbook — repeatable Revit operations

Codified, plan-agnostic versions of workflows that were originally composed
live by Blueprint. **Every operation should only ever be slow once** — the
first run discovers the method, the playbook makes it a 5-minute rerun.

## flip_plan.py — mirror-flip a house plan + fix annotation

Generalized from the Kever / Spring Mountain flip (2026-11-02, verified live:
896 elements mirrored, originals deleted, 171 labels repositioned, section
markers recut, doc saved + vision-verified).

### What it does

| Phase | Action | Writes? |
|---|---|---|
| `preflight` | doc-title gate, giant-box census, category classification, plane from walls bbox, bbox samples, warnings baseline, rollback save | one save |
| `mirror` | M2 stairs/railings **canary** → M1 building core → M3 site. Copy-semantics (`batch_mirror_elements`), doubled-verify after each batch | none |
| `delete` | W0 model groups → W1 hosts → W2 survivors → W3 stairs (only if canary verified) → W4 site. Final census vs baseline, then **save** | destructive + save |
| `annotate` | Plan-view text notes + **all** section markers mirrored across the flip line. Elevation/section view notes → review table (opt-in `--apply-view-notes`) | moves + save |
| `verify` | Census vs baseline, originals-gone check, sample mirror-check (multiset compare of centers), warnings delta, optional after-image export | read-only |
| `all` | preflight → mirror → delete → annotate → verify | — |

Phases are state-gated (`flip_state.json`) — each refuses to run unless the
previous phase completed. Rerun the failed phase to resume.

### Usage

```bash
cd barnhaus-design-agent
export REVIT_BRIDGE_URL=https://<tunnel>   # or pass --bridge / rely on bridge_sessions.json

# discovery pass on a NEW plan — see the census classification before committing
python3 playbook/flip_plan.py preflight --doc "Project Title" --axis ew --dry-run

# the real thing (ew = N<->S swap across an east-west flip line)
python3 playbook/flip_plan.py preflight --doc "Project Title" --axis ew
python3 playbook/flip_plan.py mirror
python3 playbook/flip_plan.py delete
python3 playbook/flip_plan.py annotate                 # then review the table, maybe:
python3 playbook/flip_plan.py annotate --apply-view-notes
python3 playbook/flip_plan.py verify --export          # after-images to <out>/verify/
```

`--axis ns` flips E<->W instead (mirror across a north-south line) — every
transform switches from y to x automatically.

### Decision rules baked in (Kever-proven)

- **Plane** = center of the walls bbox cross-extent → house lands back on its
  own envelope. Override with `--plane N`.
- **Canary first**: stairs/railings mirror in their own tiny batch. Revit's
  silent-rollback poison on stairs is detected via the doubled-count check; if
  it fails, originals are kept and flagged for a GUI mirror — nothing is lost.
- **Copy-semantics mirror, delete later**: elements are never mirrored+deleted
  in one step. Copies verified before originals are removed.
- **Delete waves** ordered so cascades (host deletion takes dependents with it)
  clean up naturally: groups → hosts → survivors → stairs → site.
- **Unknown categories** (not in the built-in lists) go into the mirrored set
  WITH a loud warning — review them in preflight output, exclude with
  `--exclude-cat`.
- **Annotation**:
  - Plan-view text notes: mirrored to `2·P − coord` — lands each label back in
    its room (mechanical, always applied).
  - Section markers: all mirrored (cut segments re-cover their rooms).
  - Tags/dimensions in plan views: **reported, not moved** — verify visually;
    many auto-follow their hosts.
  - Elevation/section view notes: **review table** — the script suggests
    mirror when the view's horizontal axis is the flipped axis (facing
    perpendicular to the flip normal). Semantics need eyes; apply with
    `--apply-view-notes` after looking at the exports.
- **Skip views** matching `survey`/`site` (site annotation didn't flip — the
  site didn't move). Extend with `--skip-view <substring>`.

### What the agent still does

1. Run `preflight --dry-run` on a new plan, review the census classification
   and unknown-category warnings.
2. Run the phases, watch for `!!` lines.
3. `verify --export`, then LOOK at the after-images (vision) — the script's
   checks are mechanical; the visual verdict is the agent's.
4. Review the view-note table before `--apply-view-notes`.
5. Front/Back (flip-normal-facing) elevation notes are never auto-mirrored —
   check their leaders manually after the flip.

### Timing

Kever live run (agentic, composed on the fly): ~45 min flip+annotate.
Playbook rerun: ~5–8 min end to end, most of it the two saves and the census
round-trips through the tunnel.
