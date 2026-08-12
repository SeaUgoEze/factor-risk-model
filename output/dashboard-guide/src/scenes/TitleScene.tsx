import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Chip, useEnter, useGrowX, usePop } from "../components/motion";
import { COLORS, FONT } from "../styles";

// Scene 1 - Title: brand name in serif, accent underline, tagline, capability chips.
export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const kicker = useEnter(8, -30, 20);
  const title = usePop(16, 0.92, 12);
  const underline = useGrowX(30, 14);
  const sub = useEnter(42, 40);
  const chips = useEnter(56, 34);

  // exit fade for the tail of the scene
  const exit = interpolate(frame, [128, 148], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: exit }}>
      <div
        style={{
          ...kicker,
          fontFamily: FONT.mono,
          fontSize: 30,
          letterSpacing: 9,
          color: COLORS.accent,
          marginBottom: 36,
        }}
      >
        QUANTITATIVE MODELS&ensp;·&ensp;APPLIED RESEARCH
      </div>
      <div
        style={{
          ...title,
          fontFamily: FONT.serif,
          fontSize: 168,
          fontWeight: 700,
          color: COLORS.text,
          letterSpacing: -2,
          lineHeight: 1.05,
          textAlign: "center",
          textShadow: "0 8px 70px rgba(0,0,0,0.65)",
        }}
      >
        Factor Risk Model
      </div>
      <div
        style={{
          ...underline,
          width: 250,
          height: 7,
          borderRadius: 4,
          background: COLORS.accent,
          marginTop: 42,
          boxShadow: `0 0 30px ${COLORS.accentStrong}`,
        }}
      />
      <div
        style={{
          ...sub,
          fontFamily: FONT.sans,
          fontSize: 47,
          color: COLORS.muted,
          marginTop: 40,
          textAlign: "center",
        }}
      >
        Interactive factor risk and portfolio optimization
      </div>
      <div style={{ ...chips, display: "flex", gap: 22, marginTop: 52 }}>
        <Chip>Fama-French 3 &amp; 5</Chip>
        <Chip>Optimization</Chip>
        <Chip>VaR / CVaR risk</Chip>
      </div>
    </AbsoluteFill>
  );
};
