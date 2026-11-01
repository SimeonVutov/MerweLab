import { scenarios } from '../../project';
import type { ScenarioId } from '../../project';
import styles from './CompareToolbar.module.css';

interface Props {
  left: ScenarioId;
  right: ScenarioId;
  onLeftChange: (scenario: ScenarioId) => void;
  onRightChange: (scenario: ScenarioId) => void;
  onSwap: () => void;
}

export default function CompareToolbar({ left, right, onLeftChange, onRightChange, onSwap }: Props) {
  return (
    <div className={styles.toolbar} aria-label="Comparison settings">
      <label>Left scenario <select value={left} onChange={(event) => onLeftChange(event.target.value as ScenarioId)}>
        {scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.label}</option>)}
      </select></label>
      <button onClick={onSwap} aria-label="Swap left and right scenarios">Swap</button>
      <label>Right scenario <select value={right} onChange={(event) => onRightChange(event.target.value as ScenarioId)}>
        {scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.label}</option>)}
      </select></label>
      <span>Cameras linked · shared layers and scales</span>
    </div>
  );
}
