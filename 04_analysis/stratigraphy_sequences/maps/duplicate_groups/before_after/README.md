# Before and after deduplication

The main copy now lives [inside iteration 1](../../../iter1_10082026_dedupe_strat_reports/evidence/plots/before_after/README.md). These earlier files remain available for existing links. The iteration copy has its plots, plotted-coordinate table, manifest, and reproduction method recorded together.

Open the [PNG plot](before_after_dedupe.png) or [PDF](before_after_dedupe.pdf).

The left panel maps the 166 original records in the 71 duplicate groups. The right panel maps the 75 records retained by iteration 1: 71 surviving representatives and four records farther than 100 metres from their representative. Other wells are unchanged and are outside the scope of these panels.

Both panels have identical axes, plot limits, and 5 km scale bars. Filled marker area is proportional to the number of records sharing a location. Orange rings in the before panel identify locations containing copies subsequently removed; some records at those locations survive. Green points in the after panel identify the four farther records retained.

There were 84 distinct recorded locations before and 75 after. Most removed copies shared coordinates with a survivor, so the main visible change is smaller markers rather than disappearance of every removed record. No coordinates are shifted to make coincident records look separate.

Source files are the completed iterations 0 and 1, with group membership and archives checked against iteration 1's decisions. The plot does not modify either iteration. The [manifest](manifest.json) records input/output hashes, counts, scales, and checks. [comparison_locations.csv](comparison_locations.csv) provides plotted coordinates, record counts, and original IDs.

To regenerate from the repository root:

```bash
python3 04_analysis/stratigraphy_sequences/maps/duplicate_groups/before_after/plot_before_after.py
```

The method requires Matplotlib. Coordinates and their accuracy are inherited from the source files; the scale uses the same spherical distance convention as the earlier group map.
