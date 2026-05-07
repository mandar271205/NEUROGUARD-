from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np


@dataclass
class ClientUpdate:
    client_id: str
    size: int
    before: np.ndarray
    after: np.ndarray

    @property
    def gradient(self) -> np.ndarray:
        return self.before - self.after

    def proof_inputs(self) -> dict[str, list[int] | int | str]:
        scale = 10_000
        return {
            "client_id": self.client_id,
            "modelBefore": np.round(self.before[:10] * scale).astype(int).tolist(),
            "gradients": np.round(self.gradient[:10] * scale).astype(int).tolist(),
            "modelAfter": np.round(self.after[:10] * scale).astype(int).tolist(),
            "learningRate": 1,
        }


def train_local(client_id: str, global_weights: np.ndarray, size: int, seed: int) -> ClientUpdate:
    rng = np.random.default_rng(seed)
    drift = rng.normal(loc=0.0, scale=0.02, size=global_weights.shape)
    after = global_weights + drift
    return ClientUpdate(client_id=client_id, size=size, before=global_weights.copy(), after=after)


def fedavg(updates: list[ClientUpdate]) -> np.ndarray:
    total = sum(update.size for update in updates)
    return sum(update.after * update.size for update in updates) / total


def hash_weights(weights: np.ndarray) -> str:
    packed = np.round(weights * 10_000).astype(np.int64).tobytes()
    return "0x" + hashlib.sha256(packed).hexdigest()


def main() -> None:
    global_weights = np.linspace(-0.1, 0.1, 32)
    updates = [
        train_local("college-a", global_weights, 120, 1),
        train_local("college-b", global_weights, 96, 2),
        train_local("college-c", global_weights, 108, 3),
        train_local("college-d", global_weights, 80, 4),
        train_local("college-e", global_weights, 104, 5),
    ]
    aggregate = fedavg(updates)
    print("round=1")
    print("aggregate_hash=", hash_weights(aggregate))
    print("first_client_proof_inputs=", updates[0].proof_inputs())


if __name__ == "__main__":
    main()
