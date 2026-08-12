import { AbsoluteFill, Sequence, useCurrentFrame } from "remotion";
import { AnimatedBackground } from "./components/AnimatedBackground";
import { ProgressTracker } from "./components/ProgressTracker";
import { SceneWipe } from "./components/SceneWipe";
import { TitleScene } from "./scenes/TitleScene";
import { ConfigureScene } from "./scenes/ConfigureScene";
import { RunScene } from "./scenes/RunScene";
import { ExploreScene } from "./scenes/ExploreScene";
import { CTAScene } from "./scenes/CTAScene";

export const DashboardGuide: React.FC = () => {
  const frame = useCurrentFrame();
  const active =
    frame < 130 ? -1 : frame < 235 ? 0 : frame < 340 ? 1 : frame < 445 ? 2 : 3;
  return (
    <AbsoluteFill>
      {/* Persistent layer - spans the whole video */}
      <AnimatedBackground frame={frame} />
      {/* Scenes overlap so the next starts before the current ends */}
      <Sequence from={0} durationInFrames={150}>
        <TitleScene />
      </Sequence>
      <Sequence from={130} durationInFrames={120}>
        <ConfigureScene />
      </Sequence>
      <Sequence from={235} durationInFrames={120}>
        <RunScene />
      </Sequence>
      <Sequence from={340} durationInFrames={120}>
        <ExploreScene />
      </Sequence>
      <Sequence from={445} durationInFrames={155}>
        <CTAScene />
      </Sequence>
      <SceneWipe frame={frame} />
      <ProgressTracker active={active} />
    </AbsoluteFill>
  );
};
