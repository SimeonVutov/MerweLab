"""Training loop: every episode the model proposes a full map, the environment rewards each cell."""
import numpy as np
from tqdm import tqdm

from agent import choose_actions


def train(env, model, features, allowed, model_config, training_config):
    """Returns the mean cell reward of every episode."""
    state, _ = env.reset()
    allowed_mask = allowed[state]

    # train on every cell that has a real choice (more than one allowed class)
    rows, cols = np.nonzero(allowed_mask.sum(axis=-1) > 1)
    cell_features = features[rows, cols].astype(np.float32)
    cell_allowed = allowed_mask[rows, cols]

    epsilon = training_config.epsilon_start
    mean_rewards = []

    for _ in tqdm(range(training_config.episodes)):
        state, _ = env.reset()

        # propose a map (epsilon-greedy) and get the reward of every cell
        q_values = model.predict(cell_features, batch_size=4096, verbose=0)
        actions = choose_actions(q_values, cell_allowed, epsilon)
        action_map = state.copy()
        action_map[rows, cols] = actions
        _, _, _, _, info = env.step(action_map)
        rewards = info["cell_reward"][rows, cols]

        # regression target: keep the old Q-values, replace the chosen action's Q-value by its reward
        wanted_q_values = q_values.copy()
        wanted_q_values[np.arange(len(actions)), actions] = rewards
        model.fit(cell_features, wanted_q_values,
                  epochs=model_config.epochs, batch_size=model_config.batch_size, verbose=0)

        epsilon = max(training_config.epsilon_min, epsilon * training_config.epsilon_decay)
        mean_rewards.append(rewards.mean())

    return mean_rewards