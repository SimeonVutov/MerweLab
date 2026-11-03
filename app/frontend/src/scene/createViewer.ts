import {
    Color,
    SceneMode,
    Viewer,
} from 'cesium';
import { resetCamera } from './camera';

export function createViewer(container: HTMLDivElement) {
    const viewer = new Viewer(container, {
        animation: false,
        baseLayer: false,
        baseLayerPicker: false,
        fullscreenButton: false,
        geocoder: false,
        homeButton: false,
        infoBox: false,
        navigationHelpButton: false,
        sceneMode: SceneMode.SCENE3D,
        sceneModePicker: false,
        selectionIndicator: false,
        timeline: false,
        shouldAnimate: false,
        requestRenderMode: true,
        maximumRenderTimeChange: Infinity,
        showRenderLoopErrors: false,
    });

    viewer.scene.globe.baseColor = Color.fromCssColorString('#d5ded8');
    viewer.scene.globe.depthTestAgainstTerrain = true;
    viewer.scene.screenSpaceCameraController.maximumZoomDistance = 20_000_000;
    resetCamera(viewer);
    return viewer;
}
