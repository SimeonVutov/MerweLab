import { Cartesian3, ClippingPolygon, ClippingPolygonCollection, CustomHeightmapTerrainProvider, GeographicTilingScheme, Math as CesiumMath } from 'cesium';
import type { Viewer } from 'cesium';

export type TerrainStatus = 'Loading' | 'Loaded' | 'Unavailable';
interface TerrainManifest {
    version: number;
    width: number;
    height: number;
    bounds: number[];
    coreBounds: number[];
    format: string;
    rowOrder: string;
    heightReference: string;
    scenarios: { baseline: { url: string } };
}

async function loadManifest(signal: AbortSignal): Promise<TerrainManifest> {
    const response = await fetch('/web/terrain/manifest.json', { signal });
    if (!response.ok) throw new Error(`Terrain manifest returned HTTP ${response.status}`);
    if (!response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('Terrain data is not being served. Restart the frontend server.');
    }
    const data: TerrainManifest = await response.json();
    if (data.version !== 1 || data.format !== 'float32-le' || data.rowOrder !== 'north-to-south'
        || data.heightReference !== 'WGS84 ellipsoid'
        || !Number.isInteger(data.width) || data.width < 2 || !Number.isInteger(data.height) || data.height < 2
        || data.bounds?.length !== 4 || data.coreBounds?.length !== 4
        || ![...data.bounds, ...data.coreBounds].every(Number.isFinite)) {
        throw new Error('Unsupported terrain grid');
    }
    const [west, south, east, north] = data.bounds;
    const [coreWest, coreSouth, coreEast, coreNorth] = data.coreBounds;
    if (!(west! < coreWest! && coreWest! < coreEast! && coreEast! < east!
        && south! < coreSouth! && coreSouth! < coreNorth! && coreNorth! < north!)) {
        throw new Error('Invalid terrain coverage bounds');
    }
    return data;
}

function createProvider(data: TerrainManifest, heights: Float32Array) {
    const [west, south, east, north] = data.bounds as [number, number, number, number];
    const [coreWest, coreSouth, coreEast, coreNorth] = data.coreBounds as [number, number, number, number];
    const tilingScheme = new GeographicTilingScheme();
    const size = 65;

    function sample(longitude: number, latitude: number) {
        if (longitude <= west || longitude >= east || latitude <= south || latitude >= north) return 0;
        // Interpolate the four surrounding grid samples; rows start at the northern edge.
        const x = (longitude - west) / (east - west) * (data.width - 1);
        const y = (north - latitude) / (north - south) * (data.height - 1);
        const col = Math.min(Math.floor(x), data.width - 2);
        const row = Math.min(Math.floor(y), data.height - 2);
        const dx = x - col;
        const dy = y - row;
        const index = row * data.width + col;
        const height = heights[index]! * (1 - dx) * (1 - dy) + heights[index + 1]! * dx * (1 - dy)
            + heights[index + data.width]! * (1 - dx) * dy + heights[index + data.width + 1]! * dx * dy;
        // Blend only beyond the protected CBS context; this is a display transition.
        const weight = Math.max(0, Math.min(1,
            (longitude - west) / (coreWest - west), (east - longitude) / (east - coreEast),
            (latitude - south) / (coreSouth - south), (north - latitude) / (north - coreNorth),
        ));
        return height * weight * weight * (3 - 2 * weight);
    }

    return new CustomHeightmapTerrainProvider({
        width: size,
        height: size,
        tilingScheme,
        credit: 'AHN · prepared project terrain',
        callback(x, y, level) {
            const tile = tilingScheme.tileXYToRectangle(x, y, level);
            const tileWest = CesiumMath.toDegrees(tile.west);
            const tileEast = CesiumMath.toDegrees(tile.east);
            const tileSouth = CesiumMath.toDegrees(tile.south);
            const tileNorth = CesiumMath.toDegrees(tile.north);
            const values = new Float32Array(size * size);
            if (tileEast < west || tileWest > east || tileNorth < south || tileSouth > north) return values;
            for (let row = 0; row < size; row++) {
                const latitude = tileNorth - row / (size - 1) * (tileNorth - tileSouth);
                for (let col = 0; col < size; col++) {
                    values[row * size + col] = sample(tileWest + col / (size - 1) * (tileEast - tileWest), latitude);
                }
            }
            return values;
        },
    });
}

export function createTerrainLayer(
    viewer: Viewer,
    onStatus: (status: TerrainStatus) => void,
    onError: (message: string | null) => void,
) {
    const abort = new AbortController();
    const manifest = loadManifest(abort.signal);
    const removeListeners: (() => void)[] = [];
    let clipping: ClippingPolygonCollection | undefined;
    let clippingError: string | null = null;
    let siteVisible = true;
    let siteReady = false;
    let disposed = false;

    // Cut away shared terrain only when the replacement site surface is both ready and visible.
    function updateClipping() {
        if (clipping) clipping.enabled = siteVisible && siteReady;
        viewer.scene.requestRender();
    }

    async function loadClipping() {
        const boundaryResponse = await fetch('/web/terrain/site-boundary.geojson', { signal: abort.signal });
        if (!boundaryResponse.ok) throw new Error(`Site boundary returned HTTP ${boundaryResponse.status}`);
        const boundary: { geometry: { type: string; coordinates: number[][][] } } = await boundaryResponse.json();
        const ring = boundary.geometry?.coordinates?.[0];
        if (boundary.geometry?.type !== 'Polygon' || !ring || ring.length < 4
            || !ring.every((point) => point.length === 2 && point.every(Number.isFinite))) {
            throw new Error('Invalid site terrain boundary');
        }
        if (disposed) throw new Error('Terrain disposed');
        if (!ClippingPolygonCollection.isSupported(viewer.scene)) throw new Error('Local terrain clipping requires WebGL 2 support');
        clipping = new ClippingPolygonCollection({
            polygons: [new ClippingPolygon({ positions: Cartesian3.fromDegreesArray(ring.slice(0, -1).flat()) })],
            enabled: false,
        });
        viewer.scene.globe.clippingPolygons = clipping;
        updateClipping();
    }

    async function load() {
        const data = await manifest;
        // The surroundings use one stable Current terrain; local meshes supply the scenario ground.
        const url = data.scenarios?.baseline?.url;
        if (!url || !/^\/web\/terrain\/[\w.-]+\.bin$/.test(url)) throw new Error('Missing shared terrain heights');
        const response = await fetch(url, { signal: abort.signal });
        if (!response.ok) throw new Error(`Terrain heights returned HTTP ${response.status}`);
        const buffer = await response.arrayBuffer();
        if (buffer.byteLength !== data.width * data.height * 4) throw new Error('Incomplete terrain heights');
        const heights = new Float32Array(buffer);
        if (!heights.every(Number.isFinite)) throw new Error('Invalid terrain heights');
        if (disposed) throw new Error('Terrain disposed');
        const provider = createProvider(data, heights);
        removeListeners.push(provider.errorEvent.addEventListener((cause) => {
            if (disposed || viewer.terrainProvider !== provider) return;
            onStatus('Unavailable');
            onError(`AHN terrain: ${cause.message}`);
        }));
        void loadClipping().catch((cause: unknown) => {
            if (disposed) return;
            console.error('Local terrain clipping unavailable', cause);
            clippingError = 'Local terrain mask is unavailable; site surfaces may overlap the terrain.';
            onError(clippingError);
        });
        return provider;
    }

    onStatus('Loading');
    void load().then((provider) => {
        if (disposed) return;
        if (viewer.terrainProvider !== provider) viewer.terrainProvider = provider;
        updateClipping();
        onStatus('Loaded');
        onError(clippingError);
    }).catch((cause: unknown) => {
        if (disposed) return;
        console.error('Terrain failed to load', cause);
        if (clipping) clipping.enabled = false;
        onStatus('Unavailable');
        onError(cause instanceof Error ? cause.message : 'AHN terrain could not load.');
    });

    return {
        setSiteVisible(value: boolean) { siteVisible = value; updateClipping(); },
        setSiteReady(value: boolean) { siteReady = value; updateClipping(); },
        dispose() {
            disposed = true;
            abort.abort();
            removeListeners.forEach((remove) => remove());
            if (clipping && viewer.scene.globe.clippingPolygons === clipping) {
                clipping.enabled = false;
                clipping.removeAll();
            }
        },
    };
}

export type TerrainLayer = ReturnType<typeof createTerrainLayer>;
