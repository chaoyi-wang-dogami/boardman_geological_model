# Township boundary used for location QC

`plss_townships.geojson` is a cached snapshot of the 19 Oregon Willamette Meridian township polygons from the [BLM National PLSS CadNSDI township layer](https://gis.blm.gov/arcgis/rest/services/Cadastral/BLM_Natl_PLSS_CadNSDI/MapServer/1). It was copied from the related local `bgm_burns/outputs/reference/plss_townships.geojson` cache on 2026-10-01.

The analysis validates all 19 township labels against `00_config/owrd_download.yml` before using the file. Its SHA-256 is `e993c325a03acfb5837deb04268eb8d28becb1b9e14d32d2a4dc3e560d85a596`. The snapshot is retained so reruns use the same boundary even if the live service changes.
