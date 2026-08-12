// Shared design tokens - single source of truth for the whole video.
// Palette mirrors the app's current monochrome theme (.streamlit/config.toml
// + src/analysis.py semantic chart tokens). Chrome is grayscale with a
// single #F8F8F8 functional accent; colour appears only for data meaning
// (green = positive, red = downside, amber = comparison series). No blue.

export const COLORS = {
  bg: "#101018", // canvas
  panel: "#181820", // cards / surfaces
  panelBorder: "#282830", // hairlines
  line: "#202028", // track lines
  accent: "#F8F8F8", // the single functional accent (sliders, Run, tabs)
  accentSoft: "rgba(248, 248, 248, 0.10)",
  accentStrong: "rgba(248, 248, 248, 0.35)",
  green: "#2EA043", // semantic positive (charts, "go")
  amber: "#D29922", // semantic comparison series
  danger: "#E5484D", // downside / losses
  text: "#F8F8F8",
  muted: "#8A8A92",
  faint: "#626262",
};

export const FONT = {
  // serif echoes the Times New Roman title / report branding
  serif: `Georgia, "Times New Roman", Times, serif`,
  sans: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`,
  mono: `"Cascadia Code", "JetBrains Mono", Consolas, "Courier New", monospace`,
};
