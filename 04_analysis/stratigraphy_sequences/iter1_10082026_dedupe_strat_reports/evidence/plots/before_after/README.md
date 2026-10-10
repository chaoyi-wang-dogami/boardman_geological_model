# Before and after deduplication

Open the [PNG plot](before_after_dedupe.png) or [PDF](before_after_dedupe.pdf).

The left panel maps the 166 original records in the 71 duplicate groups. The right panel maps the 75 records retained by iteration 1: 71 surviving representatives and four records farther than 100 metres from their representative. Other wells are unchanged and are outside the scope of these panels.

Both panels have identical axes, plot limits, and 5 km scale bars. Filled marker area is proportional to the number of records sharing a location. Orange rings in the before panel identify locations containing copies subsequently removed; some records at those locations survive. Green points in the after panel identify the four farther records retained.

There were 84 distinct recorded locations before and 75 after. Most removed copies shared coordinates with a survivor, so the main visible change is smaller markers rather than disappearance of every removed record. No coordinates are shifted to make coincident records look separate.

Source files are the completed iterations 0 and 1, with group membership and archives checked against iteration 1's decisions. These plots and the plotted-coordinate table were copied here unchanged on October 9, 2026, at the user's request. The [manifest](manifest.json) records input/output hashes, counts, scales, checks, and the addition. [comparison_locations.csv](comparison_locations.csv) provides plotted coordinates, record counts, and original IDs.

The previous iteration manifest and README were preserved in the parent `plots/` directory before recording this addition. Deduplication data and rules remain unchanged. The earlier copies under `maps/duplicate_groups/before_after/` remain available for existing links; this iteration directory is the main location for the deduplication comparison plots.

To reproduce in a new preview directory from the repository root:

```bash
python3 04_analysis/stratigraphy_sequences/iter1_10082026_dedupe_strat_reports/scripts/plot_before_after.py --output-dir /tmp/boardman_dedupe_plot_preview
```

The method requires Matplotlib and refuses to overwrite completed iteration files or an existing preview directory. Choose a different preview directory if the example already exists. Coordinates and their accuracy are inherited from the source files; the scale uses the same spherical distance convention as the earlier group map.
