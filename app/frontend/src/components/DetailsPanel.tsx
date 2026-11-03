import type { ReactNode } from 'react';
import CbsPanel from '../features/cbs/CbsPanel';
import type { CbsOptions } from '../features/cbs/data';
import NoisePanel from '../features/noise/NoisePanel';
import type { NoiseInfo, NoiseOptions } from '../features/noise/types';
import WindPanel from '../features/wind/WindPanel';
import type { WindInfo, WindOptions } from '../features/wind/types';
import type { Mode } from '../project';
import type { ModelStatus } from '../scene/modelLayers';
import type { TerrainStatus } from '../scene/terrain';
import styles from './DetailsPanel.module.css';

interface DetailsPanelProps {
  networkPanel: ReactNode;
  landUsePanel: ReactNode;
  environmentPanel: ReactNode;
  morphologyPanel: ReactNode;
  noise: NoiseOptions;
  noiseInfo: NoiseInfo;
  onNoiseChange: (options: NoiseOptions) => void;
  cbs: CbsOptions;
  onCbsChange: (options: CbsOptions) => void;
  open: boolean;
  mode: Mode;
  scenarioLabel: string;
  imageryVisible: boolean;
  imageryOpacity: number;
  onOpacityChange: (opacity: number) => void;
  buildingStatus: ModelStatus;
  surfaceStatus: ModelStatus;
  terrainStatus: TerrainStatus;
  wind: WindOptions;
  windInfo: WindInfo;
  onWindChange: (options: WindOptions) => void;
  comparison?: SceneDetails;
}

interface SceneDetails {
  scenarioLabel: string;
  buildingStatus: ModelStatus;
  surfaceStatus: ModelStatus;
  terrainStatus: TerrainStatus;
  windInfo: WindInfo;
  noiseInfo: NoiseInfo;
}

interface SceneSummaryProps extends SceneDetails {
  title: string;
  showWind: boolean;
}

function SceneSummary({
  title,
  buildingStatus,
  surfaceStatus,
  terrainStatus,
  windInfo,
  showWind,
}: SceneSummaryProps) {
  let sampleValue = 'No data at this location';
  if (windInfo.metric && windInfo.sample && windInfo.sample.value !== null) {
    sampleValue = `${windInfo.sample.value.toFixed(2)} ${windInfo.metric.units}`;
  }

  let sampleWarning = '';
  if (windInfo.sample?.flagged) {
    sampleWarning = ' · flagged extreme';
  } else if (windInfo.sample?.outsideRange) {
    sampleWarning = ' · outside colour range';
  }

  return (
    <section className={styles.summary} aria-label={title}>
      <details>
        <summary>{title} · layer status</summary>
        <dl className={styles.values}>
          <div>
            <dt>Context</dt>
            <dd>{buildingStatus.context}</dd>
          </div>
          <div>
            <dt>Buildings</dt>
            <dd>{buildingStatus.scenario}</dd>
          </div>
          <div>
            <dt>AHN terrain</dt>
            <dd>{terrainStatus}</dd>
          </div>
          <div>
            <dt>Site surfaces</dt>
            <dd>{surfaceStatus.scenario}</dd>
          </div>
          <div>
            <dt>Water</dt>
            <dd>{surfaceStatus.water}</dd>
          </div>
          {showWind && (
            <div>
              <dt>Wind</dt>
              <dd>{windInfo.status}</dd>
            </div>
          )}
        </dl>
      </details>
      {showWind && windInfo.error && <p role="alert" className={styles.note}>{windInfo.error}</p>}
      {showWind && windInfo.metric && windInfo.sample && (
        <p>{sampleValue}{sampleWarning}</p>
      )}
    </section>
  );
}

export default function DetailsPanel({
  networkPanel,
  landUsePanel,
  open,
  mode,
  scenarioLabel,
  imageryVisible,
  imageryOpacity,
  onOpacityChange,
  buildingStatus,
  surfaceStatus,
  terrainStatus,
  wind,
  windInfo,
  onWindChange,
  comparison,
  cbs,
  onCbsChange,
  noise,
  noiseInfo,
  onNoiseChange,
  environmentPanel,
  morphologyPanel,
}: DetailsPanelProps) {
  let displayedWindInfo = windInfo;
  if (comparison && !windInfo.metric && !windInfo.flowLegend) {
    displayedWindInfo = comparison.windInfo;
  }

  return (
    <aside id="details-panel" className={styles.panel} hidden={!open} aria-label="Details">
      <div aria-live="polite">
        <h2>{mode === 'Explore' ? 'Details' : mode}</h2>
        {mode !== 'Weather' && (
          <>
            {environmentPanel}
            {morphologyPanel}
            {networkPanel}
            {landUsePanel}
            <CbsPanel options={cbs} onChange={onCbsChange} />
            <NoisePanel
              options={noise}
              onChange={onNoiseChange}
              info={noiseInfo}
              scenarioLabel={scenarioLabel}
              comparison={comparison && {
                scenarioLabel: comparison.scenarioLabel,
                info: comparison.noiseInfo,
              }}
            />
            <SceneSummary
              title={comparison ? `Left · ${scenarioLabel}` : scenarioLabel}
              scenarioLabel={scenarioLabel}
              buildingStatus={buildingStatus}
              surfaceStatus={surfaceStatus}
              terrainStatus={terrainStatus}
              windInfo={windInfo}
              noiseInfo={noiseInfo}
              showWind={Boolean(comparison)}
            />
            {comparison && (
              <SceneSummary
                {...comparison}
                title={`Right · ${comparison.scenarioLabel}`}
                showWind
              />
            )}
            {comparison && (
              <p className={styles.note}>
                Cameras and layer settings are shared.
                {wind.metric && ' Select either map to compare values at the same location. Missing data is not zero.'}
              </p>
            )}
            <WindPanel
              info={displayedWindInfo}
              options={wind}
              onChange={onWindChange}
              showSample={!comparison}
            />
            <section className={styles.block}>
              <h2>Aerial imagery</h2>
              <label htmlFor="imagery-opacity">Opacity <output>{Math.round(imageryOpacity * 100)}%</output></label>
              <input
                id="imagery-opacity"
                type="range"
                min="0"
                max="100"
                value={Math.round(imageryOpacity * 100)}
                disabled={!imageryVisible}
                onChange={(event) => onOpacityChange(Number(event.target.value) / 100)}
              />
            </section>
          </>
        )}
      </div>
    </aside>
  );
}
