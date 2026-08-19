# 003 — Fade the pre-run info box in on load

- **Status**: DONE
- **Commit**: N/A — the working copy is unversioned (the `.git/` folder was removed by the user)
- **Severity**: LOW
- **Category**: Missed opportunities (first-view composition)
- **Estimated scope**: 1 file, ~6 lines of CSS inside one string literal

## Problem

The first screen composes in two moods. The empty-state graph under the hint
fades its grid in and then draws its curve, but the hint box above it — "Set
the configuration in the sidebar, then press ▶ Run analysis." — pops in
instantly. On a page the user sees once per load, that snap is the one
uncomposed moment left.

The hint is rendered at `factor_risk_model/interface/streamlit_app.py:498-499`
(the empty-state graph follows at `:501`, and `st.stop()` at `:502`):

```python
if not run:
    st.info("Set the configuration in the sidebar, then press **▶ Run "
            "analysis**.")
    st.markdown(_EMPTY_STATE_GRAPH, unsafe_allow_html=True)
    st.stop()
```

It renders as `[data-testid="stAlert"]` inside `[data-testid="stElementContainer"]`
(verified against the live DOM this session). Its current computed transition is
`all` (framework emotion default).

**Scope decision (read this before writing code):** the post-run warning banners
(`st.warning(w)` at `streamlit_app.py:532`) render the *same*
`[data-testid="stAlert"]`, and there is no clean CSS hook that distinguishes the
info box from a warning without content-based selectors or markup changes — both
out of scope. This plan therefore fades **all** `stAlert` mounts with the same
subtle treatment. That is deliberate and harmless: warnings also mount only
occasionally (per analysis run), and an opacity-only 0.2s fade there is
consistent with the results-block arrival (metrics and figures already fade).
Do not try to scope the selector further.

## Target

An opacity-only, 200ms strong-ease-out fade on mount via `@starting-style` — no
transform, no movement, so it cannot be perceived as motion; it only softens the
arrival. Exact CSS to add (see Steps for placement):

```css
 /* Info box (and post-run warning banners) fade in on mount - an
    opacity-only 200ms strong ease-out so the first screen composes
    with the empty-state graph instead of snapping.  st.info and
    st.warning share the stAlert testid; both mount occasionally and
    the fade is uniform.  Opacity-only, so reduced motion keeps it
    as-is (aids comprehension, no movement). */
 [data-testid="stAlert"] {
   transition: opacity .2s cubic-bezier(0.23, 1, 0.32, 1); }
 @starting-style {
   [data-testid="stAlert"] { opacity: 0; } }
```

Design notes the executor must not second-guess:

- **No reduced-motion block needed.** The animation is opacity-only — there is
  no movement to remove — and the fade is intentionally kept under reduced
  motion because it aids comprehension (the box appearing is information
  arriving). Adding a `prefers-reduced-motion` block that disables it would be
  wrong.
- **Overriding the framework's `transition: all` is safe here.** The alert has
  no hover-dependent transitions (it is a static box), unlike the Run button
  (plan 002), so a single opacity channel loses nothing.
- **`@starting-style` degrades gracefully** — engines without support show the
  box instantly; there is no stuck-invisible state because the resting style is
  full opacity.
- **No replay on widget tweaks.** Streamlit reuses identical alert nodes on
  reruns (verified for the empty-state graph in this codebase), so the fade
  plays once per mount, not on every sidebar change.

## Repo conventions to follow

- Motion is injected as CSS inside the single main `<style>` string in
  `factor_risk_model/interface/streamlit_app.py` (the `st.markdown(..., unsafe_allow_html=True)`
  call whose block ends with `</style>""", unsafe_allow_html=True)`; the figure
  entrance currently ends the block's motion rules. If plans 001 and 002 have
  been applied, their blocks precede it — add this block after whatever is
  currently last, still before `</style>`.
- Established motion vocabulary, used verbatim:
  - strong ease-out: `cubic-bezier(0.23, 1, 0.32, 1)`
  - mount-only entrances: `@starting-style` (exemplar: the figure entrance,
    `factor_risk_model/interface/streamlit_app.py` ~`:191-204`)
- The file uses CRLF line endings; keep them (a `str_replace` with `\n` matches
  fine, but do not reflow whole blocks).
- The main style string already styles `[data-testid="stAlert"]` (background,
  border, color for the monochrome theme) — do not touch those rules; only add
  the transition/`@starting-style` pair.

## Steps

1. Open `factor_risk_model/interface/streamlit_app.py` and locate the end of the
   main injected style string — the `</style>` line closing the block that also
   contains the figure entrance rules (currently ~`:204`, possibly shifted if
   plans 001/002 have since been applied; the anchor text is
   `</style>""", unsafe_allow_html=True)`).

2. Insert the full Target CSS block from the "Target" section immediately
   before that `</style>` line — i.e. replace that `</style>` line with the
   Target block followed by `</style>`.

3. Do NOT touch anything else in the file — no Python, no other CSS blocks, no
   markup, no changes to the existing `[data-testid="stAlert"]` styling rules.

## Boundaries

- Do NOT touch the empty-state graph (`_EMPTY_STATE_GRAPH`), the figure,
   metric-card, or Run-button motion, the footer, or the back-to-top iframe.
- Do NOT add movement (transform, translate) to the alert — opacity only.
- Do NOT add a reduced-motion block that disables the fade.
- Do NOT try to distinguish `st.info` from `st.warning` via content selectors or
  markup changes — the uniform treatment is the decision.
- Do NOT add new dependencies, scripts, or markup changes. CSS only.
- If the alert no longer renders as `[data-testid="stAlert"]`, or the code at
  `:498-502` no longer matches (drift since this plan was written), STOP and
  report instead of improvising.

## Verification

- **Mechanical**:
  - Syntax check: `python -c "import ast; ast.parse(open('factor_risk_model/interface/streamlit_app.py', encoding='utf-8').read())"` — must print without error.
  - App health: `curl -s -m 5 http://127.0.0.1:8501/_stcore/health` returns `ok` (the app auto-reruns on save; hard-reload the browser if the served CSS looks stale — this session has seen stale stylesheets, a reload always fixes it).
  - Computed-style check (browser console, pre-run state):
    `getComputedStyle(document.querySelector('[data-testid="stAlert"]')).transitionProperty` — must be `opacity`, and `.transitionDuration` must be `0.2s`.
  - Mechanism probe (the `@starting-style` mount fade): append a fresh
    `div` with `data-testid="stAlert"` to an `[data-testid="stElementContainer"]`
    in the console and read `getComputedStyle(el).opacity` immediately — must be
    `0` (starting style) — then after 250ms — must be `1`.
- **Feel check**: reload the app and watch the first screen:
  - The hint box fades in over 200ms in the same rhythm as the empty-state
    graph's grid fade beneath it — the screen composes, nothing snaps.
  - The fade is imperceptible as "motion" — it reads as the box simply being
    there, one frame softer.
  - Toggle `prefers-reduced-motion` (DevTools Rendering panel → emulate) and
    reload: the box still fades in (opacity only — this is intended).
  - Run the analysis: the post-run warning banners (if any) arrive with the same
    soft fade, consistent with the metric cards and figures.
- **Done when**: the pre-run hint fades in over 0.2s with the exact curve above,
  the post-run warnings share the treatment, no movement is introduced, and the
  fade remains under reduced motion.
