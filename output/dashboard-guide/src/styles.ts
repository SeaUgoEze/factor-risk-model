// Shared design tokens - single source of truth for the whole video.
// Brand palette pulled from the app's .streamlit/config.toml theme.

export const COLORS = {
  bg: "#0a0a0a",
  panel: "#121212",
  panelBorder: "#262626",
  accent: "#004d00", // deep institutional green - the one accent
  accentSoft: "rgba(121, 246, 252, 0.12)",
  accentStrong: "rgba(121, 246, 252, 0.38)",
  text: "#ededed",
  muted: "#9a9a9a",
  faint: "#545454",
  danger: "#ff6b6b",
};

export const FONT = {
  // serif echoes the Times New Roman report/cover branding
  serif: `Georgia, "Times New Roman", Times, serif`,
  sans: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`,
  mono: `"Cascadia Code", "JetBrains Mono", Consolas, "Courier New", monospace`,
};
