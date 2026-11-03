import { Cartesian3 } from 'cesium';
import type { Viewer } from 'cesium';

export function synchronizeCameras(left: Viewer, right: Viewer) {
    let active = left;
    let previous = snapshot(left);
    const removers: (() => void)[] = [];
    const inputs = [left, right].map((viewer) => ({
        viewer,
        enabled: viewer.scene.screenSpaceCameraController.enableInputs,
    }));

    function updateInputs() {
        for (const { viewer, enabled } of inputs) {
            viewer.scene.screenSpaceCameraController.enableInputs = enabled && viewer === active;
        }
    }

    function snapshot(viewer: Viewer) {
        return {
            position: Cartesian3.clone(viewer.camera.positionWC),
            direction: Cartesian3.clone(viewer.camera.directionWC),
            up: Cartesian3.clone(viewer.camera.upWC),
        };
    }

    function copy(source: Viewer, target: Viewer) {
        const pose = snapshot(source);
        target.camera.setView({
            destination: pose.position,
            orientation: { direction: pose.direction, up: pose.up },
        });
        target.scene.requestRender();
        previous = pose;
    }

    copy(left, right);
    updateInputs();

    for (const viewer of [left, right]) {
        const element = viewer.container.parentElement!;
        const activate = () => {
            if (active === viewer) {
                return;
            }

            active = viewer;
            previous = snapshot(viewer);
            updateInputs();
        };

        for (const event of ['pointerdown', 'wheel', 'focusin']) {
            element.addEventListener(event, activate, { capture: true, passive: true });
            removers.push(() => element.removeEventListener(event, activate, true));
        }

        removers.push(viewer.scene.postRender.addEventListener(() => {
            if (active !== viewer) {
                return;
            }

            const pose = snapshot(viewer);
            if (!Cartesian3.equalsEpsilon(pose.position, previous.position, 0, 0.00001)
                || !Cartesian3.equalsEpsilon(pose.direction, previous.direction, 0, 1e-10)
                || !Cartesian3.equalsEpsilon(pose.up, previous.up, 0, 1e-10)) {
                copy(viewer, viewer === left ? right : left);
            }
        }));
    }

    return () => {
        removers.forEach((remove) => remove());
        for (const { viewer, enabled } of inputs) {
            if (!viewer.isDestroyed()) {
                viewer.scene.screenSpaceCameraController.enableInputs = enabled;
            }
        }
    };
}
