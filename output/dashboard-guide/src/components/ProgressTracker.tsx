import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONT } from "../styles";

const STEPS = ["Configure", "Run", "Explore", "Try it live"];

// Persistent bottom progress tracker - the anchor the eye tracks across scenes.
export const ProgressTracker: React.FC<{ active: number }> = ({ active }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 46,
        opacity,
      }}
    >
      <div style={{ display: "flex", gap: 26, alignItems: "center" }}>
        {STEPS.map((s, i) => {
          const on = i <= active;
          return (
            <div
              key={s}
              style={{ display: "flex", alignItems: "center", gap: 12 }}
            >
              <div
                style={{
                  width: 58,
                  height: 3,
                  borderRadius: 0,
                  backgroundColor: on ? COLORS.accent : COLORS.faint,
                  boxShadow: on
                    ? `0 0 14px ${COLORS.accentStrong}`
                    : "none",
                }}
              />
              <span
                style={{
                  fontFamily: FONT.mono,
                  fontSize: 23,
                  letterSpacing: 2,
                  color: on ? COLORS.accent : COLORS.faint,
                }}
              >
                {s.toUpperCase()}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
