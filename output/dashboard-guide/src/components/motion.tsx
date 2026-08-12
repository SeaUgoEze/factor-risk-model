import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { CSSProperties } from "react";

// Lift-in: fades and rises from below (or from any offset).
export const useEnter = (delay = 0, fromY = 70, damping = 18): CSSProperties => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - delay,
    fps,
    config: { damping },
    durationInFrames: 28,
  });
  return {
    opacity: interpolate(frame, [delay, delay + 14], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
    transform: `translateY(${fromY * (1 - p)}px)`,
  };
};

// Pop: springs in with a scale, snappy/bouncy.
export const usePop = (delay = 0, from = 0.86, damping = 14): CSSProperties => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - delay,
    fps,
    config: { damping },
    durationInFrames: 32,
  });
  return {
    opacity: interpolate(frame, [delay, delay + 12], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
    transform: `scale(${from + (1 - from) * p})`,
  };
};

// GrowX: a bar that stretches horizontally from a sliver.
export const useGrowX = (delay = 0, damping = 16): CSSProperties => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: frame - delay,
    fps,
    config: { damping },
    durationInFrames: 32,
  });
  return {
    transform: `scaleX(${0.08 + 0.92 * p})`,
    transformOrigin: "center",
    opacity: interpolate(frame, [delay, delay + 10], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  };
};

// SceneLabel: the small "0X - NAME" mono kicker used in the corner of each scene.
export const SceneLabel: React.FC<{ index: string; name: string }> = ({
  index,
  name,
}) => {
  const style = useEnter(6, -24, 20);
  return (
    <div
      style={{
        ...style,
        position: "absolute",
        top: 84,
        left: 110,
        display: "flex",
        alignItems: "center",
        gap: 18,
      }}
    >
      <span
        style={{
          fontFamily: "inherit",
          fontSize: 32,
          letterSpacing: 3,
          color: "#ededed",
        }}
      >
        {index}
      </span>
      <span
        style={{
          width: 64,
          height: 2,
          background: "rgba(121, 246, 252, 0.45)",
          borderRadius: 1,
        }}
      />
      <span
        style={{
          fontSize: 32,
          letterSpacing: 4,
          color: "rgba(121, 246, 252, 0.9)",
        }}
      >
        {name}
      </span>
    </div>
  );
};

// Chip: a small bordered pill used across scenes.
export const Chip: React.FC<{
  children: React.ReactNode;
  lit?: boolean;
  style?: CSSProperties;
}> = ({ children, lit = false, style }) => (
  <div
    style={{
      padding: "14px 26px",
      borderRadius: 999,
      border: `1.5px solid ${lit ? "rgba(121,246,252,0.75)" : "#262626"}`,
      background: lit ? "rgba(121,246,252,0.10)" : "#121212",
      color: lit ? "#79F6FC" : "#9a9a9a",
      fontSize: 34,
      fontWeight: 500,
      boxShadow: lit ? "0 0 22px rgba(121,246,252,0.22)" : "none",
      ...style,
    }}
  >
    {children}
  </div>
);
