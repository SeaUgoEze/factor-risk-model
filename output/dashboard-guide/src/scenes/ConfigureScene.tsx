import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { spring } from "remotion";
import { SlidersHorizontal } from "lucide-react";
import { SceneLabel, useEnter } from "../components/motion";
import { COLORS, FONT } from "../styles";

// Scene 2 - Configure: a mock of the sidebar config panel next to the pitch line.
export const ConfigureScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const exit = interpolate(frame, [98, 118], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const panel = useEnter(8, 60, 17);
  const heading1 = useEnter(20, 50, 16);
  const heading2 = useEnter(28, 50, 16);
  const body = useEnter(38, 40, 18);

  // slider thumb travels along the track
  const thumbP = spring({ frame: frame - 46, fps, config: { damping: 16 }, durationInFrames: 34 });
  const thumbX = 0.06 + 0.52 * thumbP;

  return (
    <AbsoluteFill style={{ opacity: exit }}>
      <SceneLabel index="01" name="CONFIGURE" />
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 110,
        }}
      >
        {/* Mock sidebar panel */}
        <div
          style={{
            ...panel,
            width: 660,
            background: COLORS.panel,
            border: `1.5px solid ${COLORS.panelBorder}`,
            borderRadius: 0,
            padding: "48px 54px",
            boxShadow: "0 40px 120px rgba(0,0,0,0.55)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 18,
              fontFamily: FONT.sans,
              fontSize: 40,
              fontWeight: 600,
              color: COLORS.text,
              marginBottom: 44,
            }}
          >
            <SlidersHorizontal size={40} color={COLORS.accent} />
            Configuration
          </div>

          <Row label="Tickers">
            <div style={{ display: "flex", gap: 16 }}>
              {["AAPL", "MSFT", "NVDA"].map((t, i) => (
                <Pill key={t} delay={16 + i * 7} lit>
                  {t}
                </Pill>
              ))}
            </div>
          </Row>

          <Row label="Factor model">
            <div style={{ display: "flex", gap: 14 }}>
              <Pill delay={40} lit>
                5-Factor
              </Pill>
              <Pill delay={48}>3-Factor</Pill>
            </div>
          </Row>

          <Row label="Vol budget">              <div
                style={{
                  width: 420,
                  height: 10,
                  borderRadius: 0,
                  background: COLORS.line,
                  position: "relative",
                }}
              >
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: `${thumbX * 100}%`,
                  borderRadius: 0,
                  background: COLORS.accent,
                  boxShadow: `0 0 18px ${COLORS.accentStrong}`,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  top: -11,
                  width: 32,
                  height: 32,
                  borderRadius: 0,
                  background: COLORS.bg,
                  border: `3px solid ${COLORS.accent}`,
                  boxShadow: `0 0 20px ${COLORS.accentStrong}`,
                  left: `calc(${thumbX * 100}% - 16px)`,
                }}
              />
            </div>
          </Row>

          <Row label="Date range">
            <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
              <Pill delay={64}>2015</Pill>
              <span
                style={{
                  fontFamily: FONT.mono,
                  fontSize: 34,
                  color: COLORS.faint,
                }}
              >
                →
              </span>
              <Pill delay={70}>2019</Pill>
            </div>
          </Row>
        </div>

        {/* Pitch */}
        <div style={{ maxWidth: 620 }}>
          <div
            style={{
              ...heading1,
              fontFamily: FONT.serif,
              fontSize: 92,
              lineHeight: 1.12,
              color: COLORS.text,
            }}
          >
            Pick tickers.
          </div>
          <div
            style={{
              ...heading2,
              fontFamily: FONT.serif,
              fontSize: 92,
              lineHeight: 1.12,
              color: COLORS.text,
            }}
          >
            Set your <span style={{ color: COLORS.accent }}>mandate.</span>
          </div>
          <div
            style={{
              ...body,
              fontFamily: FONT.sans,
              fontSize: 42,
              color: COLORS.muted,
              marginTop: 36,
              lineHeight: 1.45,
            }}
          >
            Target volatility, return floor and factor tilts drive the optimizer.
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Row: React.FC<{ label: string; children: React.ReactNode }> = ({
  label,
  children,
}) => (
  <div style={{ marginBottom: 38 }}>
    <div
      style={{
        fontFamily: FONT.mono,
        fontSize: 27,
        letterSpacing: 2,
        color: COLORS.faint,
        marginBottom: 14,
      }}
    >
      {label.toUpperCase()}
    </div>
    {children}
  </div>
);

const Pill: React.FC<{
  children: React.ReactNode;
  delay: number;
  lit?: boolean;
}> = ({ children, delay, lit = false }) => {
  const style = useEnter(delay, 40, 18);
  return (
    <div
      style={{
        ...style,
        padding: "14px 30px",
        borderRadius: 0,
        border: `1.5px solid ${lit ? "rgba(248,248,248,0.7)" : COLORS.panelBorder}`,
        background: lit ? "rgba(248,248,248,0.10)" : COLORS.panel,
        color: lit ? COLORS.accent : COLORS.muted,
        fontFamily: FONT.mono,
        fontSize: 33,
        boxShadow: lit ? `0 0 20px ${COLORS.accentStrong}` : "none",
      }}
    >
      {children}
    </div>
  );
};
