# 002 — Add press feedback to the Run button

- **Status**: DONE
- **Commit**: N/A — the working copy is unversioned (the `.git/` folder was removed by the user)
- **Severity**: LOW
- **Category**: Missed opportunities (feedback gap)
- **Estimated scope**: 1 file, ~8 lines of CSS inside one string literal

## Problem

The Run button is the single most important control in the app — it launches the
whole analysis pipeline — yet it has no dedicated press response. Streamlit's
base theme gives it a hover state via a blanket `transition: all`, but there is
no tactile press-down: the click lands without any physical acknowledgment while
the user waits for a ~60s pipeline.

The button is created at `factor_risk_model/interface/streamlit_app.py:486-487`:

```python
    run = st.button(":material/play_arrow: Run analysis", type="primary",
                    width="stretch")
```

It renders as `[data-testid="stBaseButton-primary"]` (the testid sits on the
button element itself — verified against the live DOM this session). Its current
computed transition is `all` (framework emotion default), so the plan must
replace that with an explicit two-channel transition — the press scale plus a
preserved background channel for the framework's hover color change — rather
than clobbering the hover behavior.

## Target

A near-imperceptible press: `scale(0.98)` on `:active`, settling in 160ms with
the app's strong ease-out curve; background keeps its 0.2s ease transition so
the hover color behavior is preserved. Exact CSS to add (see Steps for
placement):

```css
 /* Run button press feedback - a 2% settle on :active so the click that
    starts the pipeline feels acknowledged.  Fast and subtle: 160ms strong
    ease-out.  The transform channel is new; the background channel keeps
    the framework's hover color transition alive (the emotion base sets
    transition: all, which this overrides).  :active is a press, not a
    hover, so no pointer gating is needed. */
 [data-testid="stBaseButton-primary"] {
   transition: transform 160ms cubic-bezier(0.23, 1, 0.32, 1),
               background .2s ease; }
 [data-testid="stBaseButton-primary"]:active { transform: scale(0.98); }
 @media (prefers-reduced-motion: reduce) {
   [data-testid="stBaseButton-primary"] { transition: background .2s ease; }
   [data-testid="stBaseButton-primary"]:active { transform: none; } }
```

Design notes the executor must not second-guess:

- **`scale(0.98)`, never `scale(0)`** — press feedback is a 2% settle, not a collapse.
- **Two transition channels, not one**: the emotion base style sets `transition: all`
  on this button (verified live: `getComputedStyle(...).transition === "all"`).
  Replacing it with a single `transition: transform ...` would kill the
  framework's hover background fade; the two-channel version preserves it.
  This mirrors the back-to-top's existing pattern
  (`transition: transform .25s ease, background .2s ease`,
  `factor_risk_model/interface/streamlit_app.py` iframe block).
- **No `@media (hover: hover) and (pointer: fine)` gating** — `:active` is a
  press state, not a hover state; it does not get stuck on touch.
- **Reduced motion drops the transform entirely** — press scale has no
  comprehension value, so under reduced motion the press gives background
  feedback only (`transition: background .2s ease`, `transform: none`).

## Repo conventions to follow

- Motion is injected as CSS inside the single main `<style>` string in
  `factor_risk_model/interface/streamlit_app.py` (the `st.markdown(..., unsafe_allow_html=True)`
  call whose block ends at `:204` — after plan 001 the metrics block may sit
  just before `</style>`; add this block after whatever is currently last,
  still before `</style>`).
- Established motion vocabulary, used verbatim:
  - strong ease-out: `cubic-bezier(0.23, 1, 0.32, 1)`
  - press-scale precedent: the back-to-top iframe's `transition: transform .25s ease, background .2s ease`
- The file uses CRLF line endings; keep them (a `str_replace` with `\n` matches
  fine, but do not reflow whole blocks).
- The app's CSS overrides on `[data-testid="stBaseButton-primary"]` are known to
  win over the framework's emotion styles (the monochrome restyle set its
  background, color, and border-radius successfully earlier).

## Steps

1. Open `factor_risk_model/interface/streamlit_app.py` and locate the end of the
   main injected style string — the `</style>` line that closes the block which
   also contains the figure entrance rules (currently ~`:204`, possibly shifted
   if plan 001 has since been applied; the anchor text is
   `</style>""", unsafe_allow_html=True)`).

2. Insert the full Target CSS block from the "Target" section immediately
   before that `</style>` line — i.e. replace:

   ```css
   </style>
   ```

   (the one closing the main style string, not the empty-state or footer ones)
   with the Target block followed by `</style>`.

3. Do NOT touch anything else in the file — no Python, no other CSS blocks, no
   markup, no changes to the button's Streamlit arguments.

## Boundaries

- Do NOT touch the empty-state graph (`_EMPTY_STATE_GRAPH`), the figure or
  metric-card entrances, the footer, the back-to-top iframe, or the sidebar's
  other controls.
- Do NOT change the button's appearance (colors, radius, border) — motion only.
- Do NOT add hover gating, and do NOT animate the button's `:hover` state.
- Do NOT add new dependencies, scripts, or markup changes. CSS only.
- If the button no longer renders as `[data-testid="stBaseButton-primary"]`, or
  its computed transition is no longer `all` (drift since this plan was
  written), STOP and report instead of improvising.

## Verification

- **Mechanical**:
  - Syntax check: `python -c "import ast; ast.parse(open('factor_risk_model/interface/streamlit_app.py', encoding='utf-8').read())"` — must print without error.
  - App health: `curl -s -m 5 http://127.0.0.1:8501/_stcore/health` returns `ok` (the app auto-reruns on save; hard-reload the browser if the served CSS looks stale — this session has seen stale stylesheets, a reload always fixes it).
  - Computed-style check (browser console, sidebar open):
    `getComputedStyle(document.querySelector('[data-testid="stBaseButton-primary"]')).transition` — must show `transform 0.16s cubic-bezier(0.23, 1, 0.32, 1), background 0.2s ease` (or equivalent serialization including both channels).
  - Press check: dispatch a pointer-down or hold the mouse down on the button and read `getComputedStyle(btn).transform` — must be `matrix(0.98, 0, 0, 0.98, 0, 0)` (or equivalent) while pressed, and back to `none` on release.
- **Feel check**: click **▶ Run analysis** and watch the press:
  - The button settles ~2% the instant the mouse goes down — a quick, solid "click" feel, not a sag or a bounce; it snaps back on release.
  - Hovering the button still shows the framework's background color change (the 0.2s background channel survived).
  - In DevTools Animations panel at 10% playback, the press is a clean 160ms ease-out settle and the release is equally quick.
  - Toggle `prefers-reduced-motion` (DevTools Rendering panel → emulate) and press again: no scale at all — only the background feedback remains.
- **Done when**: pressing the button gives the 2% 160ms settle with the exact curve above, the framework hover background still fades, release snaps back cleanly, and reduced motion removes the scale entirely.
