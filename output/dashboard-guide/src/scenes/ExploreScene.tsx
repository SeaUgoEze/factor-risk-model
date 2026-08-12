import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BarChart3 } from "lucide-react";
import { SceneLabel, useEnter } from "../components/motion";
import { COLORS, FONT } from "../styles";

const BARS = [
  { label: "MKT", h: 0.95 },
  { label: "SMB", h: 0.46 },
  { label: "HML", h: 0.3 },
  { label: "RMW", h: 0.14 },
  { label: "CMA", h: 0.07 },
];

const STATS = [
  { label: "Volatility", value: 17.3, suffix: "%", decimals: 1 },
  { label: "VaR 95%", value: -1.4, suffix: "%", decimals: 1 },
  { label: "CVaR", value: -2.9, suffix: "%", decimals: 1 },
];

// Scene 4 - Explore: factor loading bars growing in, live risk stat cards.
export const ExploreScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const exit = interpolate(frame, [98, 118], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const card = useEnter(8, 50, 17);
  const heading = useEnter(20, 44, 16);
  const body = useEnter(30, 36, 18);

  return (
    <AbsoluteFill style={{ opacity: exit, justifyContent: "center", alignItems: "center" }}>
      <SceneLabel index="03" name="EXPLORE" />
      <div style={{ display: "flex", alignItems: "center", gap: 110 }}>
        {/* Factor loading chart card */}
        <div
          style={{
            ...card,
            width: 760,
            background: COLORS.panel,
            border: `1.5px solid ${COLORS.panelBorder}`,
            borderRadius: 26,
            padding: "46px 52px",
            boxShadow: "0 40px 120px rgba(0,0,0,0.55)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              fontFamily: FONT.sans,
              fontSize: 38,
              fontWeight: 600,
              color: COLORS.text,
              marginBottom: 40,
            }}
          >
            <BarChart3 size={38} color={COLORS.accent} />
            Factor loadings
          </div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 46, height: 340 }}>
            {BARS.map((b, i) => {
              const p = spring({
                frame: frame - (16 + i * 9),
                fps,
                config: { damping: 17 },
                durationInFrames: 30,
              });
              const h = b.h * 300 * Math.max(0, p);
              return (
                <div
                  key={b.label}
                  style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}
                >
                  <div
                    style={{
                      width: 74,
                      height: h,
                      borderRadius: "10px 10px 4px 4px",
                      background: `linear-gradient(180deg, ${COLORS.accent}, rgba(121,246,252,0.35))`,
                      boxShadow: `0 0 26px ${COLORS.accentStrong}`,
                    }}
                  />
                  <div
                    style={{
                      marginTop: 18,
                      fontFamily: FONT.mono,
                      fontSize: 29,
                      color: COLORS.muted,
                      letterSpacing: 1,
                    }}
                  >
                    {b.label}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Pitch + stats */}
        <div style={{ maxWidth: 620 }}>
          <div
            style={{
              ...heading,
              fontFamily: FONT.serif,
              fontSize: 82,
              lineHeight: 1.14,
              color: COLORS.text,
            }}
          >
            Exposures.
            <br />
            Risk.
            <br />
            <span style={{ color: COLORS.accent }}>Stress tests.</span>
          </div>
          <div
            style={{
              ...body,
              fontFamily: FONT.sans,
              fontSize: 40,
              color: COLORS.muted,
              marginTop: 34,
              lineHeight: 1.4,
            }}
          >
            Live numbers across every tab of the dashboard.
          </div>

          {/* Stat cards */}
          <div style={{ display: "flex", gap: 20, marginTop: 44 }}>
            {STATS.map((s, i) => {
              const style = useEnter(36 + i * 8, 40, 18);
              const val = interpolate(frame, [42 + i * 8, 90 + i * 8], [0, s.value], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              });
              return (
                <div
                  key={s.label}
                  style={{
                    ...style,
                    flex: 1,
                    background: COLORS.panel,
                    border: `1.5px solid ${COLORS.panelBorder}`,
                    borderRadius: 18,
                    padding: "24px 26px",
                  }}
                >
                  <div
                    style={{
                      fontFamily: FONT.mono,
                      fontSize: 25,
                      letterSpacing: 1,
                      color: COLORS.faint,
                      marginBottom: 10,
                    }}
                  >
                    {s.label.toUpperCase()}
                  </div>
                  <div
                    style={{
                      fontFamily: FONT.mono,
                      fontSize: 46,
                      color: s.value < 0 ? "#ffb3b3" : COLORS.accent,
                    }}
                  >
                    {val.toFixed(s.decimals)}
                    {s.suffix}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
