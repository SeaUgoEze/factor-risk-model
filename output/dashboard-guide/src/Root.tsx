import { Composition } from "remotion";
import { DashboardGuide } from "./DashboardGuide";

export const RemotionRoot = () => (
  <Composition
    id="DashboardGuide"
    component={DashboardGuide}
    durationInFrames={600}
    fps={30}
    width={1920}
    height={1080}
  />
);
