import { BoundingSphere, Cartesian3, Intersect, SceneTransforms } from 'cesium';
import type { Viewer } from 'cesium';
import type { ScenarioId } from '../project';

export function createBuildingOutlines(viewer: Viewer, onError: (message: string) => void) {
    const abort = new AbortController();
    const loaded = new Map<string, { positions: Cartesian3[]; bounds: BoundingSphere }[]>();
    const pending = new Set<string>();
    const canvas = document.createElement('canvas');
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;display:none';
    canvas.setAttribute('aria-hidden', 'true');
    viewer.scene.canvas.parentElement!.appendChild(canvas);
    const context = canvas.getContext('2d');
    let manifestRequest: Promise<{ groups: Record<string, string> }> | undefined;
    let scenario: ScenarioId = 'baseline';
    let enabled = false;
    let contextVisible = true;
    let scenarioVisible = true;
    let disposed = false;
    let dirty = true;
    let previousPose = '';

    async function readJson(url: string) {
        if (!/^\/web\/building-outlines\/[\w.-]+$/.test(url) || url.includes('..')) {
            throw new Error('Invalid building outline URL');
        }
        const response = await fetch(url, { signal: abort.signal });
        if (!response.ok || response.headers.get('content-type')?.includes('text/html')) {
            throw new Error('Building outline asset unavailable');
        }
        if (url.endsWith('.gz') && !response.headers.get('content-encoding')?.includes('gzip')) {
            if (!response.body) {
                throw new Error('Empty outline asset');
            }
            return new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json();
        }
        return response.json();
    }

    async function load(group: string) {
        if (pending.has(group) || loaded.has(group)) {
            return;
        }
        pending.add(group);
        try {
            if (!manifestRequest) {
                manifestRequest = readJson('/web/building-outlines/manifest.json').catch((error: unknown) => {
                    manifestRequest = undefined;
                    throw error;
                });
            }
            const manifest = await manifestRequest;
            const data: { lines: number[][] } = await readJson(manifest.groups[group]!);
            if (disposed) {
                return;
            }
            if (!Array.isArray(data.lines) || !data.lines.every((ring) => ring.length >= 12
                && ring.length % 3 === 0 && ring.every(Number.isFinite))) {
                throw new Error('Invalid building outline geometry');
            }

            loaded.set(group, data.lines.map((ring) => {
                const positions = Cartesian3.fromDegreesArrayHeights(ring);
                return { positions, bounds: BoundingSphere.fromPoints(positions) };
            }));
            dirty = true;
            viewer.scene.requestRender();
        } catch (error) {
            if (!disposed) {
                onError(error instanceof Error ? error.message : 'Building outlines could not load');
            }
        } finally {
            pending.delete(group);
        }
    }

    function draw() {
        if (!enabled || disposed || !context) {
            return;
        }
        const width = viewer.scene.canvas.clientWidth;
        const height = viewer.scene.canvas.clientHeight;
        const ratio = window.devicePixelRatio || 1;
        const camera = viewer.camera;
        const pose = [camera.positionWC.x, camera.positionWC.y, camera.positionWC.z,
            camera.directionWC.x, camera.directionWC.y, camera.directionWC.z,
            camera.upWC.x, camera.upWC.y, camera.upWC.z, camera.frustum.projectionMatrix.toString(),
            width, height, ratio].join(':');
        if (!dirty && pose === previousPose) {
            return;
        }
        previousPose = pose;
        dirty = false;
        canvas.width = Math.round(width * ratio);
        canvas.height = Math.round(height * ratio);
        context.setTransform(ratio, 0, 0, ratio, 0, 0);
        context.clearRect(0, 0, width, height);
        context.beginPath();

        const groups = [];
        if (contextVisible) {
            groups.push('shared');
        }
        if (scenarioVisible) {
            groups.push(scenario);
        }
        const visible = camera.frustum.computeCullingVolume(camera.positionWC, camera.directionWC, camera.upWC);
        for (const group of groups) {
            for (const ring of loaded.get(group) ?? []) {
                if (visible.computeVisibility(ring.bounds) === Intersect.OUTSIDE) {
                    continue;
                }
                const points = ring.positions.map((point) => SceneTransforms.worldToWindowCoordinates(viewer.scene, point));
                if (points.some((point) => !point)) {
                    continue;
                }
                if (points.every((point) => point!.x < 0) || points.every((point) => point!.x > width)
                    || points.every((point) => point!.y < 0) || points.every((point) => point!.y > height)) {
                    continue;
                }
                context.moveTo(points[0]!.x, points[0]!.y);
                for (const point of points.slice(1)) {
                    context.lineTo(point!.x, point!.y);
                }
            }
        }

        // A separate screen overlay guarantees outlines remain above every map, including elevated noise/wind surfaces.
        context.strokeStyle = '#ffffff';
        context.lineWidth = 3;
        context.stroke();
        context.strokeStyle = '#142022';
        context.lineWidth = 1.3;
        context.stroke();
    }

    const removeRender = viewer.scene.postRender.addEventListener(draw);

    return {
        setOptions(mode2d: boolean, selected: ScenarioId, contextEnabled: boolean, designEnabled: boolean) {
            enabled = mode2d;
            scenario = selected;
            contextVisible = contextEnabled;
            scenarioVisible = designEnabled;
            dirty = true;
            canvas.style.display = enabled ? 'block' : 'none';
            if (enabled) {
                void load('shared');
                void load(scenario);
            }
            viewer.scene.requestRender();
        },
        dispose() {
            disposed = true;
            abort.abort();
            removeRender();
            canvas.remove();
            loaded.clear();
        },
    };
}
