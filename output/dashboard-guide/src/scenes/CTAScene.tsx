import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import {
  ArrowUpRight,
  ExternalLink,
  Globe,
  ShieldCheck,
} from "lucide-react";
import { useEnter, usePop } from "../components/motion";
import { COLORS, FONT } from "../styles";

const URL = "seanezeocha-factor-risk-model.streamlit.app";

// Scene 5 - CTA: try it live, the URL pill, no-install badges, the button.
export const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const heading = usePop(8, 0.9, 12);
  const button = usePop(22, 0.85, 11);
  const urlPill = useEnter(36, 60, 16);
  const badges = useEnter(52, 40, 18);
  const sub = useEnter(16, 30, 18);

  const exit = interpolate(frame, [136, 154], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // gentle pulse on the URL pill
  const pulse = 1 + Math.sin(frame / 11) * 0.012;

  return (
    <AbsoluteFill style={{ opacity: exit, justifyContent: "center", alignItems: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div
          style={{
            ...heading,
            fontFamily: FONT.serif,
            fontSize: 148,
            fontWeight: 700,
            color: COLORS.text,
            textAlign: "center",
            textShadow: "0 8px 70px rgba(0,0,0,0.65)",
          }}
        >
          Try it <span style={{ color: COLORS.accent }}>live</span>
        </div>

        <div
          style={{
            ...sub,
            fontFamily: FONT.sans,
            fontSize: 42,
            color: COLORS.muted,
            marginTop: 26,
          }}
        >
          No downloads. Runs in your browser.
        </div>

        {/* Button */}
        <div
          style={{
            ...button,
            marginTop: 56,
            display: "flex",
            alignItems: "center",
            gap: 18,
            padding: "26px 58px",
            borderRadius: 999,
            background: `linear-gradient(160deg, ${COLORS.accent}, #4fd8e0)`,
            boxShadow: `0 0 60px ${COLORS.accentStrong}, 0 24px 50px rgba(0,0,0,0.5)`,
            fontFamily: FONT.sans,
            fontSize: 44,
            fontWeight: 700,
            color: "#0a0a0a",
          }}
        >
          Open the dashboard
          <ArrowUpRight size={46} color="#0a0a0a" strokeWidth={2.6} />
        </div>

        {/* URL pill */}
        <div
          style={{
            ...urlPill,
            marginTop: 46,
            display: "flex",
            alignItems: "center",
            gap: 20,
            padding: "20px 40px",
            borderRadius: 999,
            background: COLORS.panel,
            border: `1.5px solid ${COLORS.accentStrong}`,
            transform: `scale(${pulse})`,
            boxShadow: `0 0 40px rgba(121,246,252,0.12)`,
          }}
        >
          <ExternalLink size={38} color={COLORS.accent} />
          <span
            style={{
              fontFamily: FONT.mono,
              fontSize: 44,
              color: COLORS.accent,
              letterSpacing: 0.5,
            }}
          >
            {URL}
          </span>
        </div>

        {/* Badges */}
        <div style={{ ...badges, display: "flex", gap: 22, marginTop: 40 }}>
          <Badge>
            <ShieldCheck size={30} color={COLORS.accent} /> No install
          </Badge>
          <Badge>
            <Globe size={30} color={COLORS.accent} /> Runs in your browser
          </Badge>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Badge: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "14px 28px",
      borderRadius: 999,
      border: `1.5px solid ${COLORS.panelBorder}`,
      background: COLORS.panel,
      color: COLORS.muted,
      fontFamily: FONT.sans,
      fontSize: 33,
    }}
  >
    {children}
  </div>
);
