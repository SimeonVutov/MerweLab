import type { CbsOptions } from '../features/cbs/data';
import type { EnvironmentOptions } from '../features/environment/types';
import { landUseMaps } from '../features/landUse/types';
import type { LandUseOptions } from '../features/landUse/types';
import { morphologyIndicators } from '../features/morphology/data';
import type { MorphologyOptions } from '../features/morphology/data';
import type { NetworkOptions } from '../features/network/types';
import type { NoiseOptions } from '../features/noise/types';
import type { WindOptions } from '../features/wind/types';
import { layerGroups } from '../project';
import type { LayerId } from '../project';
import styles from './LayerPanel.module.css';

interface LayerPanelProps {
    network: NetworkOptions;
    onNetworkChange: (options: NetworkOptions) => void;
    landUse: LandUseOptions;
    onLandUseChange: (options: LandUseOptions) => void;
    environment: EnvironmentOptions;
    onEnvironmentChange: (options: EnvironmentOptions) => void;
    morphology: MorphologyOptions;
    onMorphologyChange: (options: MorphologyOptions) => void;
    noise: NoiseOptions;
    onNoiseChange: (options: NoiseOptions) => void;
    cbs: CbsOptions;
    onCbsChange: (options: CbsOptions) => void;
    open: boolean;
    imageryVisible: boolean;
    onImageryChange: (visible: boolean) => void;
    contextVisible: boolean;
    scenarioVisible: boolean;
    onContextChange: (visible: boolean) => void;
    onScenarioChange: (visible: boolean) => void;
    groundVisible: boolean;
    waterVisible: boolean;
    onGroundChange: (visible: boolean) => void;
    onWaterChange: (visible: boolean) => void;
    wind: WindOptions;
    onWindChange: (options: WindOptions) => void;
}

export default function LayerPanel({
    network,
    onNetworkChange,
    landUse,
    onLandUseChange,
    environment,
    onEnvironmentChange,
    morphology,
    onMorphologyChange,
    open,
    imageryVisible,
    onImageryChange,
    contextVisible,
    scenarioVisible,
    onContextChange,
    onScenarioChange,
    groundVisible,
    waterVisible,
    onGroundChange,
    onWaterChange,
    wind,
    onWindChange,
    cbs,
    onCbsChange,
    noise,
    onNoiseChange,
}: LayerPanelProps) {
    const controls: Partial<Record<LayerId, { checked: boolean; change: (visible: boolean) => void }>> = {
        roads: {
            checked: network.paths,
            change: (paths) => onNetworkChange({ ...network, paths }),
        },
        entrances: {
            checked: network.entrances,
            change: (entrances) => onNetworkChange({ ...network, entrances }),
        },
        'garage-ramp': {
            checked: network.ramp,
            change: (ramp) => onNetworkChange({ ...network, ramp }),
        },
        'unbuilt-paths': {
            checked: network.candidates,
            change: (candidates) => onNetworkChange({ ...network, candidates }),
        },
        trees: {
            checked: environment.trees,
            change: (trees) => onEnvironmentChange({ ...environment, trees }),
        },
        'elevation-colours': {
            checked: environment.elevation,
            change: (elevation) => onEnvironmentChange({ ...environment, elevation }),
        },
        noise: {
            checked: noise.enabled,
            change: (enabled) => onNoiseChange({ ...noise, enabled }),
        },
        cbs: {
            checked: cbs.enabled,
            change: (enabled) => onCbsChange({ ...cbs, enabled }),
        },
        aerial: {
            checked: imageryVisible,
            change: onImageryChange,
        },
        'context-buildings': {
            checked: contextVisible,
            change: onContextChange,
        },
        'scenario-buildings': {
            checked: scenarioVisible,
            change: onScenarioChange,
        },
        'site-surfaces': {
            checked: groundVisible,
            change: onGroundChange,
        },
        water: {
            checked: waterVisible,
            change: onWaterChange,
        },
        'wind-speed': {
            checked: wind.metric === 'speed',
            change: (checked) => onWindChange({ ...wind, metric: checked ? 'speed' : null }),
        },
        turbulence: {
            checked: wind.metric === 'turbulence',
            change: (checked) => onWindChange({ ...wind, metric: checked ? 'turbulence' : null }),
        },
        'wind-pressure': {
            checked: wind.metric === 'pressure',
            change: (checked) => onWindChange({ ...wind, metric: checked ? 'pressure' : null }),
        },
        'wind-arrows': {
            checked: wind.arrows,
            change: (checked) => onWindChange({ ...wind, arrows: checked }),
        },
        'streamlines-2d': {
            checked: wind.streamlines_2d,
            change: (checked) => onWindChange({ ...wind, streamlines_2d: checked }),
        },
        'streamlines-3d': {
            checked: wind.streamlines_3d,
            change: (checked) => onWindChange({ ...wind, streamlines_3d: checked }),
        },
    };

    const standardGroups = layerGroups.filter((group) => (
        group.label !== 'Morphology' && group.label !== 'Land use'
    ));
    const expandedGroups = ['Models', 'Environment', 'Morphology', 'Society', 'Wind & noise', 'Mobility'];

    function toggleMorphologyIndicator(id: string, enabled: boolean) {
        const layer = { ...morphology.layers[id]!, enabled };

        onMorphologyChange({
            ...morphology,
            layers: { ...morphology.layers, [id]: layer },
        });
    }

    function toggleLandUseMap(id: typeof landUseMaps[number]['id'], enabled: boolean) {
        const layer = { ...landUse.layers[id], enabled };

        onLandUseChange({
            ...landUse,
            layers: { ...landUse.layers, [id]: layer },
        });
    }

    return (
        <aside id="layer-panel" className={styles.panel} hidden={!open} aria-label="Layers">
            <h2>Layers</h2>
            <p className={styles.note}>Greyed layers are not connected yet.</p>
            <details open>
                <summary>Morphology</summary>
                {morphologyIndicators.map(([id, label]) => (
                    <label key={id} className={styles.layer}>
                        <input
                            type="checkbox"
                            checked={morphology.layers[id]?.enabled ?? false}
                            onChange={(event) => toggleMorphologyIndicator(id, event.target.checked)}
                        />
                        {label}
                    </label>
                ))}
            </details>
            <details open>
                <summary>Land use</summary>
                {landUseMaps.map(({ id, label }) => (
                    <label key={id} className={styles.layer}>
                        <input
                            type="checkbox"
                            checked={landUse.layers[id].enabled}
                            onChange={(event) => toggleLandUseMap(id, event.target.checked)}
                        />
                        {label}
                    </label>
                ))}
            </details>
            {standardGroups.map((group) => (
                <details key={group.label} open={expandedGroups.includes(group.label)}>
                    <summary>{group.label}</summary>
                    {group.layers.map((layer) => {
                        const control = controls[layer.id];

                        return (
                            <label
                                key={layer.id}
                                className={control ? styles.layer : styles.unavailable}
                                title={control ? undefined : 'Not connected yet'}
                            >
                                <input
                                    type="checkbox"
                                    disabled={!control}
                                    checked={control?.checked ?? false}
                                    onChange={(event) => control?.change(event.target.checked)}
                                />
                                {layer.label}
                            </label>
                        );
                    })}
                </details>
            ))}
        </aside>
    );
}
