import { Cartesian3, HeadingPitchRange, Matrix4, Math as CesiumMath } from 'cesium';
import type { Viewer } from 'cesium';

export function resetCamera(viewer: Viewer) {
  viewer.camera.lookAt(
    Cartesian3.fromDegrees(4.416, 51.9116),
    new HeadingPitchRange(0, CesiumMath.toRadians(-45), 2200),
  );
  viewer.camera.lookAtTransform(Matrix4.IDENTITY);
  viewer.scene.requestRender();
}
