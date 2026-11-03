export const landUseMaps = [
    { id: 'existing', label: 'Existing land use' },
    { id: 'optimized', label: 'Optimized proposal' },
    { id: 'changes', label: 'Changed cells' },
] as const;

export type LandUseMapId = typeof landUseMaps[number]['id'];
export type LandUsePane = 'single' | 'left' | 'right';
export type LandUseTarget = 'both' | 'left' | 'right';

export interface LandUseLayerOptions {
    enabled: boolean;
    opacity: number;
    target: LandUseTarget;
}

export interface LandUseOptions {
    layers: Record<LandUseMapId, LandUseLayerOptions>;
    focusRequest: number;
}

export interface LandUseLocation {
    longitude: number;
    latitude: number;
}

export interface LandUseSample {
    outside: boolean;
    existing: number | null;
    optimized: number | null;
}

export const initialLandUseOptions: LandUseOptions = {
    layers: {
        existing: { enabled: false, opacity: 0.75, target: 'both' },
        optimized: { enabled: false, opacity: 0.75, target: 'both' },
        changes: { enabled: false, opacity: 0.9, target: 'both' },
    },
    focusRequest: 0,
};

export function hasLandUseLayers(options: LandUseOptions) {
    return landUseMaps.some(({ id }) => options.layers[id].enabled);
}

export function visibleLandUseMaps(options: LandUseOptions, pane: LandUsePane) {
    return landUseMaps.filter(({ id }) => {
        const layer = options.layers[id];
        if (!layer.enabled) return false;

        return pane === 'single' || layer.target === 'both' || layer.target === pane;
    });
}
