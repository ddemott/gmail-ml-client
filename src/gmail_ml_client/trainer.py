from .data_store import fetch_for_training
from .model import train


def train_from_feedback(epochs: int = 6) -> tuple[str, list[str]]:
    texts, labels = fetch_for_training()
    if not texts:
        return "No labeled feedback yet. Use `cli.py review` to add some.", []
    report, classes = train(texts, labels, epochs=epochs)
    return report, classes
