import os

working_dir = os.path.join(os.getcwd(), "working")
os.makedirs(working_dir, exist_ok=True)

import random
import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader, TensorDataset

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

experiment_data = {
    name: {
        "metrics": {"train": [], "val": []},
        "losses": {"train": [], "val": []},
        "predictions": [],
        "ground_truth": [],
        "epochs": [],
        "test_metrics": [],
        "test_losses": [],
        "shortcut_ablation_accuracy": [],
    }
    for name in ("stable_only", "shortcut_exposed", "late_masked")
}


def make_data(n, seed, split):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, size=n).astype(np.float32)
    sign = 2 * y - 1
    stable = sign + rng.normal(0, 1.0, n)
    if split == "test":
        q_sign = rng.choice([-1.0, 1.0], size=n)
    else:
        agrees = rng.random(n) < 0.95
        q_sign = sign * np.where(agrees, 1.0, -1.0)
    shortcut = q_sign + rng.normal(0, 0.35, n)
    return np.column_stack([stable, shortcut]).astype(np.float32), y[:, None]


class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2, 16), nn.ReLU(), nn.Linear(16, 16), nn.ReLU(), nn.Linear(16, 1)
        )

    def forward(self, x):
        return self.net(x)


def evaluate(model, loader):
    model.eval()
    loss_fn = nn.BCEWithLogitsLoss(reduction="sum")
    total_loss, correct, count = 0.0, 0, 0
    with torch.no_grad():
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            logits = model(xb)
            total_loss += loss_fn(logits, yb).item()
            correct += ((logits >= 0) == (yb >= 0.5)).sum().item()
            count += len(yb)
    return total_loss / count, correct / count


conditions = ("stable_only", "shortcut_exposed", "late_masked")
for seed in range(10):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    x_train_raw, y_train_raw = make_data(2048, 1000 + seed, "train")
    x_val_raw, y_val_raw = make_data(512, 2000 + seed, "val")
    x_test_raw, y_test_raw = make_data(2048, 3000 + seed, "test")

    mean = x_train_raw.mean(axis=0, keepdims=True)
    std = x_train_raw.std(axis=0, keepdims=True) + 1e-6
    x_train = (x_train_raw - mean) / std
    x_val = (x_val_raw - mean) / std
    x_test = (x_test_raw - mean) / std
    y_train = y_train_raw
    y_val = y_val_raw
    y_test = y_test_raw

    for condition in conditions:
        model = MLP().to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        train_ds = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train))
        train_loader = DataLoader(train_ds, batch_size=128, shuffle=True)
        val_loader = DataLoader(
            TensorDataset(torch.from_numpy(x_val), torch.from_numpy(y_val)),
            batch_size=256,
            shuffle=False,
        )
        history = experiment_data[condition]
        for epoch in range(5):
            model.train()
            total_loss, correct, count = 0.0, 0, 0
            for xb, yb in train_loader:
                batch = {"x": xb, "y": yb}
                batch = {
                    k: v.to(device)
                    for k, v in batch.items()
                    if isinstance(v, torch.Tensor)
                }
                inputs = batch["x"].clone()
                if condition == "stable_only":
                    inputs[:, 1] = 0
                elif condition == "late_masked" and epoch >= 3:
                    inputs[:, 1] = 0
                optimizer.zero_grad()
                logits = model(inputs)
                loss = nn.functional.binary_cross_entropy_with_logits(
                    logits, batch["y"]
                )
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * len(batch["y"])
                correct += ((logits.detach() >= 0) == (batch["y"] >= 0.5)).sum().item()
                count += len(batch["y"])

            train_loss, train_acc = total_loss / count, correct / count
            val_loss, val_acc = evaluate(model, val_loader)
            history["losses"]["train"].append(train_loss)
            history["losses"]["val"].append(val_loss)
            history["metrics"]["train"].append(train_acc)
            history["metrics"]["val"].append(val_acc)
            history["epochs"].append(epoch + 1)
            print(
                f"Seed {seed} | {condition} | Epoch {epoch + 1}: validation_loss = {val_loss:.4f}, validation_accuracy = {val_acc:.4f}"
            )

        test_x = torch.from_numpy(x_test).to(device)
        test_y = torch.from_numpy(y_test).to(device)
        model.eval()
        with torch.no_grad():
            test_logits = model(test_x)
            test_loss = nn.functional.binary_cross_entropy_with_logits(
                test_logits, test_y
            ).item()
            test_pred = (test_logits >= 0).float()
            test_acc = (test_pred == test_y).float().mean().item()
            val_ablate = torch.from_numpy(x_val).to(device).clone()
            val_ablate[:, 1] = 0
            ablate_pred = (model(val_ablate) >= 0).float()
            ablate_acc = (
                (ablate_pred == torch.from_numpy(y_val).to(device))
                .float()
                .mean()
                .item()
            )

        history["test_metrics"].append(test_acc)
        history["test_losses"].append(test_loss)
        history["shortcut_ablation_accuracy"].append(ablate_acc)
        history["predictions"].append(test_pred.cpu().numpy().squeeze())
        history["ground_truth"].append(y_test.squeeze())


def bootstrap_ci(values, seed=77, iterations=5000):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, (iterations, len(values)), replace=True).mean(axis=1)
    return values.mean(), np.quantile(samples, 0.025), np.quantile(samples, 0.975)


for condition in conditions:
    acc = experiment_data[condition]["test_metrics"]
    loss = experiment_data[condition]["test_losses"]
    mean, lo, hi = bootstrap_ci(acc)
    print(
        f"{condition}: shortcut-free test accuracy={mean:.3f} (95% bootstrap CI {lo:.3f}, {hi:.3f}), "
        f"test loss={np.mean(loss):.3f}, correlated-val ablation accuracy="
        f'{np.mean(experiment_data[condition]["shortcut_ablation_accuracy"]):.3f}'
    )

for condition in conditions[1:]:
    differences = np.asarray(experiment_data[condition]["test_metrics"]) - np.asarray(
        experiment_data["stable_only"]["test_metrics"]
    )
    mean, lo, hi = bootstrap_ci(differences)
    print(
        f"{condition} minus stable_only test accuracy: {mean:.3f} "
        f"(95% paired bootstrap CI {lo:.3f}, {hi:.3f})"
    )

np.save(
    os.path.join(working_dir, "experiment_data.npy"), experiment_data, allow_pickle=True
)

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for condition in conditions:
    val_loss = np.asarray(experiment_data[condition]["losses"]["val"]).reshape(10, 5)
    val_acc = np.asarray(experiment_data[condition]["metrics"]["val"]).reshape(10, 5)
    axes[0].plot(np.arange(1, 6), val_loss.mean(axis=0), marker="o", label=condition)
    axes[1].plot(np.arange(1, 6), val_acc.mean(axis=0), marker="o", label=condition)
axes[0].set(title="Validation loss", xlabel="Epoch", ylabel="BCE loss")
axes[1].set(title="Validation accuracy", xlabel="Epoch", ylabel="Accuracy")
for ax in axes:
    ax.grid(alpha=0.25)
    ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(working_dir, "shortcut_recovery_learning_curves.png"), dpi=160)
plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4))
means = [np.mean(experiment_data[c]["test_metrics"]) for c in conditions]
cis = [bootstrap_ci(experiment_data[c]["test_metrics"]) for c in conditions]
errors = [[m - lo for m, lo, hi in cis], [hi - m for m, lo, hi in cis]]
ax.bar(
    conditions, means, yerr=errors, capsize=4, color=["#4c78a8", "#f58518", "#54a24b"]
)
ax.set(ylabel="Shortcut-free test accuracy", ylim=(0, 1), title="Recovery comparison")
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig(os.path.join(working_dir, "shortcut_recovery_test_accuracy.png"), dpi=160)
plt.close(fig)
