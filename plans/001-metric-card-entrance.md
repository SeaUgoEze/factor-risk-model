# 001 — Add the fade-up entrance to the results metric cards

- **Status**: TODO
- **Commit**: N/A — the working copy is unversioned (the `.git/` folder was removed by the user)
- **Severity**: MEDIUM
- **Category**: Missed opportunities (results-block arrival cohesion)
- **Estimated scope**: 1 file, ~20 lines of CSS inside one string literal

## Problem

When the analysis completes, the results block appears all at once. The chart
figures already fade up (`streamlit_app.py:191-204`), but the four metric cards
at the top of the results view snap in instantly. The block therefore arrives in
two different moods: the numbers teleport, the charts glide. This is the one
remaining jarring beat in an otherwise deliberate results-arrival sequence.

Current code, verbatim (`factor_risk_model/interface/streamlit_app.py:191-204`):

```css
 /* Chart figures fade up as they mount after a run - a single, subtle
    reveal that stops the results block from teleporting in.  Pure CSS
    @starting-style (mount-only, no JS state): unsupported engines just
    show the image instantly, so there is no stuck-invisible risk.
    transform + opacity only; strong ease-out, 300ms. */
 [data-testid="stImageContainer"] img {
   transition: opacity .3s cubic-bezier(0.23, 1, 0.32, 1),
               transform .3s cubic-bezier(0.23, 1, 0.32, 1); }
 @starting-style {
   [data-testid="stImageContainer"] img {
     opacity: 0; transform: translateY(8px); } }
 @media (prefers-reduced-motion: reduce) {
   [data-testid="stImageContainer"] img {
     transition: opacity .2s ease; transform: none; } }
```

The metrics row is built at `factor_risk_model/interface/streamlit_app.py:525-529`:

```python
m = result.risk_summary.loc["Optimal"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Annualized return", fmt_pct(m["ann_return_%"] / 100))
c2.metric("Annualized vol", fmt_pct(m["ann_vol_%"] / 100))
c3.metric("Sharpe ratio", f"{m['sharpe']:.2f}")
c4.metric("Max drawdown", fmt_pct(m["max_drawdown_%"] / 100))
```

Streamlit renders each card as `[data-testid="stMetric"]` inside a
`[data-testid="stColumn"]`; the four columns of a `st.columns(4)` call are
siblings inside one `[data-testid="stHorizontalBlock"]`, so
`:nth-of-type(n)` indexes them reliably. (Verified against this Streamlit
version's live DOM: `[data-testid="stMetric"]` and `[data-testid="stImageContainer"]`
both exist.)

## Target

The four cards enter exactly like the figures — same curve, same duration, same
mount-only `@starting-style` — plus a 40ms cascade so the row reads as one
deliberate arrival instead of a single block. Exact CSS to add (see Steps for
placement):

```css
 /* Metric cards fade up with the figures so the whole results block
    arrives as one system - same recipe as the figure entrance:
    @starting-style mount-only, strong ease-out, 300ms, with a 40ms
    cascade across the four cards.  The :has() guard keeps the stagger
    off other column rows (tables, export buttons). */
 [data-testid="stMetric"] {
   transition: opacity .3s cubic-bezier(0.23, 1, 0.32, 1),
               transform .3s cubic-bezier(0.23, 1, 0.32, 1); }
 @starting-style {
   [data-testid="stMetric"] {
     opacity: 0; transform: translateY(8px); } }
 @media (prefers-reduced-motion: no-preference) {
   [data-testid="stColumn"]:nth-of-type(2):has([data-testid="stMetric"])
     [data-testid="stMetric"] { transition-delay: .04s; }
   [data-testid="stColumn"]:nth-of-type(3):has([data-testid="stMetric"])
     [data-testid="stMetric"] { transition-delay: .08s; }
   [data-testid="stColumn"]:nth-of-type(4):has([data-testid="stMetric"])
     [data-testid="stMetric"] { transition-delay: .12s; } }
 @media (prefers-reduced-motion: reduce) {
   [data-testid="stMetric"] {
     transition: opacity .2s ease; transform: none; transition-delay: 0s; } }
```

Design notes the executor must not second-guess:

- **`transition-delay` lives inside `@media (prefers-reduced-motion: no-preference)`** because the stagger selectors out-specify a plain reduced-motion reset; scoping them there means reduced-motion users get the delay-free opacity fade for free.
- **`:has()` guards the stagger** so the other `st.columns(...)` rows in the app (`streamlit_app.py:553`, `:573`, `:586`, `:625`) never inherit a delay. If `:has()` is unsupported, the guard fails harmlessly — no stagger, entrance still works.
- **`translateY(8px)`, never `scale(0)`**, and the entrance ends fully visible — no stuck-invisible state because `@starting-style` degrades to instant on unsupported engines.

## Repo conventions to follow

- Motion is injected as CSS inside the single main `<style>` string in `factor_risk_model/interface/streamlit_app.py` (the `st.markdown(..., unsafe_allow_html=True)` call whose block ends at `:204`). Add the new rules inside that same string, immediately after the figure block.
- The app's established motion vocabulary, used verbatim:
  - strong ease-out: `cubic-bezier(0.23, 1, 0.32, 1)`
  - strong ease-in-out: `cubic-bezier(0.77, 0, 0.175, 1)` (not used here — entrances use ease-out)
  - mount-only entrances: `@starting-style`
  - reduced motion: keep an opacity fade, drop movement — exactly what the figure block at `:203-204` does.
- The file uses CRLF line endings; keep them (a `str_replace` with `\n` matches fine, but do not reflow whole blocks).

## Steps

1. Open `factor_risk_model/interface/streamlit_app.py` and locate the end of the figure entrance block — the exact text:

   ```css
    @media (prefers-reduced-motion: reduce) {
      [data-testid="stImageContainer"] img {
        transition: opacity .2s ease; transform: none; } }
   </style>"""", unsafe_allow_html=True)
   ```

   (lines ~203-205; the `</style>` closes the main injected style string).

2. Insert the full Target CSS block from the "Target" section between the figure block's closing `}` and the `</style>` line — i.e. replace:

   ```css
        transition: opacity .2s ease; transform: none; } }
   </style>
   ```

   with:

   ```css
        transition: opacity .2s ease; transform: none; } }
    /* Metric cards fade up with the figures so the whole results block
       arrives as one system - same recipe as the figure entrance:
       @starting-style mount-only, strong ease-out, 300ms, with a 40ms
       cascade across the four cards.  The :has() guard keeps the stagger
       off other column rows (tables, export buttons). */
    [data-testid="stMetric"] {
      transition: opacity .3s cubic-bezier(0.23, 1, 0.32, 1),
                  transform .3s cubic-bezier(0.23, 1, 0.32, 1); }
    @starting-style {
      [data-testid="stMetric"] {
        opacity: 0; transform: translateY(8px); } }
    @media (prefers-reduced-motion: no-preference) {
      [data-testid="stColumn"]:nth-of-type(2):has([data-testid="stMetric"])
        [data-testid="stMetric"] { transition-delay: .04s; }
      [data-testid="stColumn"]:nth-of-type(3):has([data-testid="stMetric"])
        [data-testid="stMetric"] { transition-delay: .08s; }
      [data-testid="stColumn"]:nth-of-type(4):has([data-testid="stMetric"])
        [data-testid="stMetric"] { transition-delay: .12s; } }
    @media (prefers-reduced-motion: reduce) {
      [data-testid="stMetric"] {
        transition: opacity .2s ease; transform: none; transition-delay: 0s; } }
   </style>
   ```

3. Do NOT touch anything else in the file — no Python, no other CSS blocks, no markup.

## Boundaries

- Do NOT touch the empty-state graph (`_EMPTY_STATE_GRAPH`), the figure entrance, the footer, the back-to-top iframe, or the sidebar.
- Do NOT animate the warning banners, dataframes, or tab bar — out of scope.
- Do NOT add new dependencies, scripts, or markup changes. CSS only.
- Do NOT restyle the metric cards (colors, borders, fonts) — motion properties only.
- If the code at `:191-204` or `:525-529` no longer matches (drift since this plan was written), STOP and report instead of improvising.

## Verification

- **Mechanical**:
  - Syntax check: `python -c "import ast; ast.parse(open('factor_risk_model/interface/streamlit_app.py', encoding='utf-8').read())"` — must print without error.
  - App health: `curl -s -m 5 http://127.0.0.1:8501/_stcore/health` returns `ok` (the app auto-reruns on save; hard-reload the browser if the served CSS looks stale — this session has seen stale stylesheets, a reload always fixes it).
  - DOM check (post-run, via the browser console): `document.querySelectorAll('[data-testid="stMetric"]').length` is 4, and each has `getComputedStyle(el).transitionProperty === "opacity, transform"` and `opacity` settling at `1` (no stuck-invisible cards).
  - Stagger check: the second/third/fourth `[data-testid="stMetric"]` elements report `getComputedStyle(el).transitionDelay` of `0.04s` / `0.08s` / `0.12s`; the first is `0s`.
- **Feel check**: reload the app, click **▶ Run analysis**, and watch the results land:
  - The four metric cards fade up 8px with a 40ms cascade while the figures below do the same — one system, not two moods.
  - In DevTools Animations panel at 10% playback, the cards rise smoothly (strong ease-out: fast start, soft landing), no bounce, no slide-through.
  - Toggle `prefers-reduced-motion` (DevTools Rendering panel → emulate) and re-run: cards fade via opacity only — no vertical movement, no stagger, still visible.
  - Check one other `st.columns` row (e.g. the Export tab) — nothing there is delayed or animated by this change.
- **Done when**: all four cards enter with the exact curve/duration/stagger above under normal settings, degrade to an instant, fully-visible row on engines without `@starting-style`, and become a plain 0.2s opacity fade under reduced motion.
