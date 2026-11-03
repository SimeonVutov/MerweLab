import {
    Cartographic, ImageryLayer, Math as CesiumMath, Rectangle,
    ScreenSpaceEventHandler, ScreenSpaceEventType, SingleTileImageryProvider,
    TextureMagnificationFilter, TextureMinificationFilter,
} from 'cesium';
import type { Cartesian2, Viewer } from 'cesium';
import { loadLandUse } from './data';
import type { LandUseData } from './data';
import { hasLandUseLayers, initialLandUseOptions, visibleLandUseMaps } from './types';
import type { LandUseLocation, LandUseMapId, LandUseOptions, LandUsePane } from './types';

export function createLandUseLayers(
    viewer: Viewer,
    onProbe: (point: LandUseLocation) => void,
    onError: (message: string | null) => void,
) {
    const loaded = new Map<LandUseMapId, ImageryLayer>();
    const pending = new Map<LandUseMapId, Promise<ImageryLayer>>();
    const handler = new ScreenSpaceEventHandler(viewer.canvas);
    let options = initialLandUseOptions;
    let pane: LandUsePane = 'single';
    let generation = 0;
    let disposed = false;
    let focusRequest = options.focusRequest;

    function requestLayer(id: LandUseMapId, data: LandUseData) {
        const cached = pending.get(id);
        if (cached) return cached;

        const map = data.maps.find((item) => item.id === id)!;
        const rectangle = Rectangle.fromDegrees(...data.bounds);
        const request = SingleTileImageryProvider.fromUrl(map.image, { rectangle }).then((provider) => {
            const layer = new ImageryLayer(provider, { show: false });
            // Nearest sampling keeps class edges crisp instead of blending categories.
            layer.minificationFilter = TextureMinificationFilter.NEAREST;
            layer.magnificationFilter = TextureMagnificationFilter.NEAREST;
            if (disposed) {
                layer.destroy();
                return layer;
            }

            viewer.imageryLayers.add(layer);
            loaded.set(id, layer);
            return layer;
        }).catch((error: unknown) => {
            pending.delete(id);
            throw error;
        });

        pending.set(id, request);
        return request;
    }

    async function update() {
        const request = ++generation;
        const wanted = visibleLandUseMaps(options, pane);
        for (const [id, layer] of loaded) {
            layer.show = wanted.some((map) => map.id === id);
        }

        viewer.scene.requestRender();
        if (wanted.length === 0) {
            onError(null);
            return;
        }

        try {
            const data = await loadLandUse();
            if (disposed || request !== generation) return;

            for (const { id } of wanted) {
                const layer = loaded.get(id) ?? await requestLayer(id, data);
                if (disposed || request !== generation) return;

                layer.show = true;
                layer.alpha = options.layers[id].opacity;
                viewer.imageryLayers.raiseToTop(layer);
            }

            onError(null);
            viewer.scene.requestRender();
        } catch (error) {
            if (!disposed && request === generation) {
                onError(error instanceof Error ? error.message : 'Land-use maps could not load');
            }
        }
    }

    handler.setInputAction(({ position }: { position: Cartesian2 }) => {
        if (visibleLandUseMaps(options, pane).length === 0) return;

        const ray = viewer.camera.getPickRay(position);
        const point = ray && viewer.scene.globe.pick(ray, viewer.scene);
        if (!point) return;

        const location = Cartographic.fromCartesian(point);
        onProbe({ longitude: CesiumMath.toDegrees(location.longitude), latitude: CesiumMath.toDegrees(location.latitude) });
    }, ScreenSpaceEventType.LEFT_CLICK);

    return {
        setOptions(value: LandUseOptions, side: LandUsePane) {
            const shouldFocus = value.focusRequest !== focusRequest;
            options = value;
            pane = side;
            focusRequest = value.focusRequest;
            void update();

            // Visibility and opacity never move the camera. Only the explicit area
            // button requests a new view, including in synchronized comparison panes.
            if (shouldFocus && hasLandUseLayers(value)) {
                void loadLandUse().then((data) => {
                    if (disposed || focusRequest !== value.focusRequest) return;

                    viewer.camera.cancelFlight();
                    viewer.camera.setView({ destination: Rectangle.fromDegrees(...data.bounds) });
                    viewer.scene.requestRender();
                }).catch((error: unknown) => {
                    if (!disposed) onError(error instanceof Error ? error.message : 'Land-use area unavailable');
                });
            }
        },
        dispose() {
            disposed = true;
            generation++;
            handler.destroy();
            for (const layer of loaded.values()) {
                viewer.imageryLayers.remove(layer, true);
            }
        },
    };
}
