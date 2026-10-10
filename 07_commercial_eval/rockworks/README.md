# RockWorks evaluation

This directory contains everything specific to evaluating RockWorks 2026 for the Boardman geological model.

## Directory layout

```text
rockworks/
├── README.md
├── devdoc/                 # Dated evaluation decisions and findings
│   ├── index.md
│   └── YYYY-MM-DD/
├── input/                  # RockWorks-ready test inputs and manifests
├── project/                # Local RockWorks project/database files
├── exports/                # Data exported from RockWorks for round-trip checks
├── figures/                # Screenshots and exported evaluation figures
└── scripts/                # Reproducible preparation and comparison code
```

The existing processed Boardman files remain authoritative. RockWorks inputs are derived copies, and RockWorks exports never overwrite source data.

Start with [the evaluation notes](devdoc/index.md).
