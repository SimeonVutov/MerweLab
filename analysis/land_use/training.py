import numpy as np
from tqdm import tqdm

from agent import choose_actions


def pick_random(cells, how_many):
    how_many = min(len(cells), how_many)
    return cells[np.random.choice(len(cells), size=how_many, replace=False)]


def train(env, model, features, allowed, model_config, training_config):
    changing_cells = np.argwhere(env.start != env.target)
    same_cells = np.argwhere(env.start == env.target)

    epsilon = training_config.epsilon_start
    mean_rewards = []

    for _ in tqdm(range(training_config.episodes)):
        state, _ = env.reset()

        cells = np.vstack([
            pick_random(changing_cells, training_config.changing_cells_per_episode),
            pick_random(same_cells, training_config.same_cells_per_episode),
        ])
        rows, cols = cells[:, 0], cells[:, 1]
        cell_features = features[rows, cols]
        allowed_mask = allowed[state[rows, cols]]

        q_values = model.predict(cell_features, verbose=0)
        actions = choose_actions(q_values, allowed_mask, epsilon)

        action_map = state.copy()
        action_map[rows, cols] = actions

        _, _, _, _, info = env.step(action_map)
        rewards = info["cell_reward"][rows, cols]

        wanted_q_values = q_values.copy()
        wanted_q_values[np.arange(len(actions)), actions] = rewards
        model.fit(cell_features, wanted_q_values,
                  epochs=model_config.epochs, batch_size=model_config.batch_size, verbose=0)

        epsilon = max(training_config.epsilon_min, epsilon * training_config.epsilon_decay)
        mean_rewards.append(rewards.mean())

    return mean_rewards