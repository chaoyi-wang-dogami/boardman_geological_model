import csv
from pathlib import Path
import matplotlib.pyplot as plt

files = sorted(Path("/home/chaoyiwang/workspace/boardman_geological_model/01_raw/wells").rglob("lithology.csv"))
counts = []

for path in files:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = csv.reader(f)
        next(rows, None)  # Skip header
        count = sum(any(cell.strip() for cell in row) for row in rows)
    if count:
        counts.append(count)

print(f"Wells with non-empty lithology: {len(counts)}")
print(f"Total lithology files checked: {len(files)}")

if not counts:
    raise SystemExit("No lithology data found.")

ranges = [(1, 1), (2, 10), (11, 20), (21, 30),
          (31, 40), (41, 50), (51, 60)]
labels = ["1", "10", "20", "30", "40", "50", "60"]
frequencies = [
    sum(low <= count <= high for count in counts)
    for low, high in ranges
]

if max(counts) > 60:
    labels.append(">60")
    frequencies.append(sum(count > 60 for count in counts))

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(labels, frequencies, width=0.95,
              color="steelblue", edgecolor="white")
ax.bar_label(bars, padding=3)
ax.set_xlabel("Lithology rows per well")
ax.set_ylabel("Number of wells")
ax.set_title(f"Lithology row counts — {len(counts)}/{len(files)} wells")
ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
ax.margins(y=0.15)
fig.text(0.5, 0.02,
         "Bins: 1; 10; 20; 30; 40; 50; 60; >60",
         ha="center", fontsize=9)
fig.tight_layout(rect=[0, 0.05, 1, 1])

output = Path("/home/chaoyiwang/workspace/boardman_geological_model/05_notebooks/figures/lithology_row_counts.png")
output.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(output, dpi=200)
print(f"Histogram saved to: {output}")
plt.show()