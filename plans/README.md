# Animation Improvement Plans

Self-contained implementation plans produced by `improve-animations`. Executors
can pick up any plan with zero context from the conversation that produced it —
each plan inlines exact values, file paths, and verification steps.

| # | Plan | Severity | Status |
| --- | --- | --- | --- |
| 001 | Add the fade-up entrance to the results metric cards | MEDIUM | DONE |
| 002 | Add press feedback to the Run button | LOW | DONE |
| 003 | Fade the pre-run info box in on load | LOW | DONE |

## Recommended execution order

All three plans were applied in one pass (001 → 002 → 003) into the same main
`<style>` string in `factor_risk_model/interface/streamlit_app.py`, each
anchoring on the closing `</style>` line.

1. **001 — Metric-card entrance** — completes the results-arrival story the
   figure entrance already started (MEDIUM; the highest-leverage item).
2. **002 — Run button press feedback** — press-scale on the core action.
3. **003 — Info-box fade** — first-screen composition, consistent with the
   results-block arrival (fades `st.info` and `st.warning` alike).

## Verification summary (2026-08-09)

All three applied and verified live against the running app:

- **001** — metric cards report `transition: opacity 0.3s, transform 0.3s` with
  `transition-delay` `0s / 0.04s / 0.08s / 0.12s` across the four cards, and
  settle at opacity 1 after the `@starting-style` mount fade.
- **002** — Run button reports `transition: transform 0.16s cubic-bezier(0.23, 1, 0.32, 1), background 0.2s`;
  the `:active { transform: scale(0.98) }` rule is served.
- **003** — info box reports `transition: opacity 0.2s cubic-bezier(0.23, 1, 0.32, 1)` with the
  `@starting-style` fade applied (starts 0, settles 1).

Note: the preview webview's animation timeline intermittently freezes (a
rendering-throttle artifact that also affects the pre-existing animations and
screenshots). Forcing the pending transitions to completion confirmed every
element's correct end state; in a normal browser the fades play at their
specified durations.

## Notes

- Plans are stamped with the git commit at write time; all three are stamped
  `N/A` because this working copy is unversioned (the `.git/` folder was
  removed by the user) — re-verify file:line references against the code
  before executing.
- `improve-animations reconcile` can refresh stale file:line references if the
  code drifts.
