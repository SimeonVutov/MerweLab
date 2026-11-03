import { scenarios } from '../project';
import type { Mode, ScenarioId } from '../project';
import styles from './Header.module.css';

interface HeaderProps {
    mode: Mode;
    scenarioId: ScenarioId;
    onModeChange: (mode: Mode) => void;
    onScenarioChange: (scenarioId: ScenarioId) => void;
}

export default function Header({ mode, scenarioId, onModeChange, onScenarioChange }: HeaderProps) {
    const modes: Mode[] = ['Explore', 'Compare', 'Weather'];

    return (
        <header className={styles.header}>
            <span className={styles.brand}>MerweLab</span>
            <nav className={styles.modes} aria-label="Mode">
                {modes.map((item) => (
                    <button
                        key={item}
                        aria-pressed={mode === item}
                        onClick={() => onModeChange(item)}
                    >
                        {item}
                    </button>
                ))}
            </nav>
            <div
                className={styles.scenarios}
                role="group"
                aria-label="Scenario"
                hidden={mode === 'Weather'}
            >
                {scenarios.map((scenario) => (
                    <button
                        key={scenario.id}
                        aria-pressed={scenarioId === scenario.id}
                        onClick={() => onScenarioChange(scenario.id)}
                    >
                        {scenario.label}
                    </button>
                ))}
            </div>
        </header>
    );
}
