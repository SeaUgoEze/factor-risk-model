import { AbsoluteFill } from "remotion";
import { COLORS } from "../styles";

// Persistent background: radial accent glow that drifts, faint dot grid, vignette.
export const AnimatedBackground: React.FC<{ frame: number }> = ({ frame }) => {
  const drift = Math.sin(frame / 45) * 60;
  const glowY = 200 + Math.sin(frame / 60) * 50;
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg }}>
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(1100px 700px at 50% ${glowY}px, ${COLORS.accentSoft}, transparent 70%)`,
          transform: `translateX(${drift}px) scale(1.12)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage:
            "radial-gradient(circle, rgba(255,255,255,0.045) 1.5px, transparent 1.5px)",
          backgroundSize: "52px 52px",
          WebkitMaskImage:
            "radial-gradient(circle at 50% 45%, black 20%, transparent 78%)",
          maskImage:
            "radial-gradient(circle at 50% 45%, black 20%, transparent 78%)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 50% 42%, transparent 45%, rgba(0,0,0,0.5) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};
