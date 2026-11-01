import type { Mode } from '../project';
import styles from './DetailsPanel.module.css';
import type { ModelStatus } from '../scene/modelLayers';
import type { TerrainStatus } from '../scene/terrain';
import WindPanel from '../features/wind/WindPanel';
import type { WindInfo, WindOptions } from '../features/wind/types';

interface DetailsPanelProps {
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
}

function SceneSummary({ title, buildingStatus, surfaceStatus, terrainStatus, windInfo, showWind }: SceneDetails & { title: string; showWind: boolean }) {
  return (
    <section className={styles.summary} aria-label={title}>
      <h2>{title}</h2>
      <dl className={styles.values}>
        <div><dt>Context</dt><dd>{buildingStatus.context}</dd></div>
        <div><dt>Buildings</dt><dd>{buildingStatus.scenario}</dd></div>
        <div><dt>AHN terrain</dt><dd>{terrainStatus}</dd></div>
        <div><dt>Site surfaces</dt><dd>{surfaceStatus.scenario}</dd></div>
        <div><dt>Water</dt><dd>{surfaceStatus.water}</dd></div>
        {showWind && <div><dt>Wind</dt><dd>{windInfo.status}</dd></div>}
      </dl>
      {showWind && windInfo.error && <p role="alert" className={styles.note}>{windInfo.error}</p>}
      {showWind && windInfo.metric && windInfo.sample && <p>
        {windInfo.sample.value === null ? 'No data at this location' : `${windInfo.sample.value.toFixed(2)} ${windInfo.metric.units}`}
        {windInfo.sample.flagged ? ' · flagged extreme' : windInfo.sample.outsideRange ? ' · outside colour range' : ''}
      </p>}
    </section>
  );
}

export default function DetailsPanel({
  open, mode, scenarioLabel, imageryVisible, imageryOpacity, onOpacityChange, buildingStatus, surfaceStatus,
  terrainStatus, wind, windInfo, onWindChange, comparison,
}: DetailsPanelProps) {
  return (
    <aside id="details-panel" className={styles.panel} hidden={!open} aria-label="Details">
      <div aria-live="polite">
        <h2>{mode === 'Explore' ? scenarioLabel : mode}</h2>
        {mode !== 'Weather' && (
          <>
            <SceneSummary title={comparison ? `Left · ${scenarioLabel}` : scenarioLabel}
              scenarioLabel={scenarioLabel} buildingStatus={buildingStatus} surfaceStatus={surfaceStatus}
              terrainStatus={terrainStatus} windInfo={windInfo} showWind={Boolean(comparison)} />
            {comparison && <>
              <SceneSummary {...comparison} title={`Right · ${comparison.scenarioLabel}`} showWind />
              <p className={styles.note}>Layer visibility and opacity apply to both maps. Move either view to navigate both.</p>
              {wind.metric && <p className={styles.note}>Select a location on either map to read both scenarios at the same coordinates. Missing data is not zero.</p>}
            </>}
            <WindPanel info={comparison && !windInfo.metric && !windInfo.flowLegend ? comparison.windInfo : windInfo}
              options={wind} onChange={onWindChange} showSample={!comparison} />
            <section className={styles.block}>
              <h2>Aerial imagery</h2>
              <p className={styles.note}>PDOK · latest 25 cm imagery</p>
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
        {mode === 'Weather' && <p className={styles.note}>Weather visualization to be agreed.</p>}
      </div>
    </aside>
  );
}
