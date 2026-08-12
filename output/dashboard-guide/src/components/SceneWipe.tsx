import { AbsoluteFill, interpolate } from "remotion";
import { COLORS } from "../styles";

const BOUNDARIES = [130, 235, 340, 445];

// A soft light-sweep that plays at each scene boundary.
export const SceneWipe: React.FC<{ frame: number }> = ({ frame }) => {
  const boundary = BOUNDARIES.find((b) => frame >= b && frame <= b + 18);
  if (boundary === undefined) {
    return null;
  }
  const p = (frame - boundary) / 18;
  const x = interpolate(p, [0, 1], [-0.25, 1.25]);
  const opacity = interpolate(p, [0, 0.12, 0.85, 1], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ justifyContent: "center" }}>
      <div
        style={{
          position: "absolute",
          left: `${x * 100}%`,
          width: "26%",
          height: 110,
          background: `linear-gradient(90deg, transparent, ${COLORS.accentStrong}, transparent)`,
          filter: "blur(3px)",
          opacity,
          transform: "skewX(-18deg)",
        }}
      />
    </AbsoluteFill>
  );
};
