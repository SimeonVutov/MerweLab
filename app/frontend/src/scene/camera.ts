import { Cartesian3, HeadingPitchRange, Matrix4, Rectangle, Math as CesiumMath } from 'cesium';
import type { Viewer } from 'cesium';

export type ViewMode = '2d' | '3d';

export function resetCamera(viewer: Viewer, mode: ViewMode = '3d') {
  viewer.camera.cancelFlight();
  viewer.scene.screenSpaceCameraController.enableTilt = mode === '3d';
  viewer.scene.screenSpaceCameraController.enableLook = mode === '3d';
  if (mode === '2d') {
    viewer.camera.setView({
      destination: Rectangle.fromDegrees(4.399, 51.899, 4.452, 51.925),
      orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 },
    });
    viewer.scene.requestRender();
    return;
  }

  viewer.camera.lookAt(
    Cartesian3.fromDegrees(4.416, 51.9116),
    new HeadingPitchRange(0, CesiumMath.toRadians(-45), 2200),
  );
  viewer.camera.lookAtTransform(Matrix4.IDENTITY);
  viewer.scene.requestRender();
}
