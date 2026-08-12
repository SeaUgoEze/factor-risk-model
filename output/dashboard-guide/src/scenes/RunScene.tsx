import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Play } from "lucide-react";
import { SceneLabel, useEnter, usePop } from "../components/motion";
import { COLORS, FONT } from "../styles";

const NODES = ["Exposures", "Optimize", "Risk", "Stress", "Anomaly"];

// Scene 3 - Run: play button, running progress bar, pipeline nodes lighting up.
export const RunScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const exit = interpolate(frame, [98, 118], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const play = usePop(10, 0.7, 11);
  const progress = interpolate(frame, [22, 106], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const heading = useEnter(34, 40, 17);

  // ring pulse after press
  const ring = spring({ frame: frame - 12, fps, config: { damping: 12 }, durationInFrames: 20 });

  return (
    <AbsoluteFill style={{ opacity: exit, justifyContent: "center", alignItems: "center" }}>
      <SceneLabel index="02" name="RUN ANALYSIS" />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        {/* Play button */}
        <div style={{ position: "relative", marginBottom: 54 }}>
          <div
            style={{
              position: "absolute",
              inset: -26,
              borderRadius: "50%",
              border: `2px solid ${COLORS.accentStrong}`,
              transform: `scale(${1 + (1 - ring) * 0.35})`,
              opacity: ring * 0.6,
            }}
          />
          <div
            style={{
              ...play,
              width: 168,
              height: 168,
              borderRadius: 0,
              background: COLORS.accent,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: `0 0 70px ${COLORS.accentStrong}, 0 30px 60px rgba(0,0,0,0.5)`,
            }}
          >
            <Play
              size={72}
              color={COLORS.bg}
              fill={COLORS.bg}
              style={{ marginLeft: 10 }}
            />
          </div>
        </div>

        {/* Progress bar */}
        <div
          style={{
            width: 860,
            height: 12,
            borderRadius: 0,
            background: COLORS.line,
            overflow: "hidden",
            marginBottom: 58,
          }}
        >
          <div
            style={{
              width: `${progress * 100}%`,
              height: "100%",
              borderRadius: 0,
              background: COLORS.accent,
              boxShadow: `0 0 24px ${COLORS.accentStrong}`,
            }}
          />
        </div>

        {/* Pipeline nodes */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 60 }}>
          {NODES.map((n, i) => {
            const on = frame >= 26 + i * 17;
            return (
              <div key={n} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div
                  style={{
                    padding: "14px 28px",
                    borderRadius: 0,
                    border: `1.5px solid ${on ? "rgba(248,248,248,0.75)" : COLORS.panelBorder}`,
                    background: on ? "rgba(248,248,248,0.10)" : COLORS.panel,
                    color: on ? COLORS.accent : COLORS.faint,
                    fontFamily: FONT.sans,
                    fontSize: 33,
                    fontWeight: 500,
                    boxShadow: on ? `0 0 22px ${COLORS.accentStrong}` : "none",
                  }}
                >
                  {n}
                </div>
                {i < NODES.length - 1 && (
                  <div
                    style={{
                      width: 34,
                      height: 2,
                      background: frame >= 26 + i * 17 + 8 ? COLORS.accent : COLORS.faint,
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>

        <div
          style={{
            ...heading,
            fontFamily: FONT.serif,
            fontSize: 74,
            color: COLORS.text,
            textAlign: "center",
          }}
        >
          One click runs the full pipeline.
        </div>
      </div>
    </AbsoluteFill>
  );
};
