BEGIN;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA boardman;
SET search_path TO boardman,public;
CREATE TABLE iterations (
  iteration_number integer PRIMARY KEY,
  directory_name text NOT NULL UNIQUE,
  purpose text NOT NULL,
  source_status text NOT NULL,
  dataset_parent integer REFERENCES iterations,
  is_data_release boolean NOT NULL
);
CREATE TABLE source_files (
  source_id text PRIMARY KEY CHECK(length(source_id)=64),
  size_bytes bigint NOT NULL,
  content_gzip bytea NOT NULL
);
CREATE TABLE source_locations (
  path text PRIMARY KEY,
  source_id text NOT NULL REFERENCES source_files,
  iteration_number integer REFERENCES iterations,
  role text NOT NULL
);
CREATE TABLE source_records (
  record_id uuid PRIMARY KEY,
  source_id text NOT NULL REFERENCES source_files,
  csv_record integer NOT NULL CHECK(csv_record>=2),
  raw_values jsonb NOT NULL,
  UNIQUE(source_id,csv_record)
);
CREATE TABLE wells (well_id text PRIMARY KEY CHECK(well_id<>''));
CREATE TABLE well_versions (
  record_id uuid PRIMARY KEY REFERENCES source_records,
  well_id text NOT NULL REFERENCES wells,
  latitude numeric,
  longitude numeric,
  completed_depth_ft numeric,
  location geometry(Point,4326),
  horizontal_reference_status text NOT NULL DEFAULT 'EPSG4326_display_assumption_source_unverified'
);
CREATE INDEX well_version_well_idx ON well_versions(well_id);
CREATE INDEX well_location_idx ON well_versions USING gist(location);
CREATE TABLE intervals (
  interval_id uuid PRIMARY KEY,
  well_id text NOT NULL REFERENCES wells,
  kind text NOT NULL CHECK(kind IN ('stratigraphy','lithology')),
  baseline_record_id uuid NOT NULL UNIQUE REFERENCES source_records
);
CREATE TABLE interval_versions (
  record_id uuid PRIMARY KEY REFERENCES source_records,
  interval_id uuid NOT NULL REFERENCES intervals,
  top_depth_ft numeric,
  bottom_depth_ft numeric,
  top_elevation_ft numeric,
  bottom_elevation_ft numeric,
  thickness_ft numeric,
  strat_unit text,
  material_raw text
);
CREATE INDEX interval_version_interval_idx ON interval_versions(interval_id);
CREATE TABLE well_membership (
  iteration_number integer NOT NULL REFERENCES iterations,
  well_id text NOT NULL REFERENCES wells,
  version_record_id uuid NOT NULL REFERENCES well_versions,
  state text NOT NULL CHECK(state IN ('working','deduplicated','excluded_no_stratigraphy')),
  PRIMARY KEY(iteration_number,well_id)
);
CREATE TABLE interval_membership (
  iteration_number integer NOT NULL REFERENCES iterations,
  interval_id uuid NOT NULL REFERENCES intervals,
  version_record_id uuid NOT NULL REFERENCES interval_versions,
  state text NOT NULL CHECK(state IN ('working','deduplicated','excluded_no_stratigraphy')),
  PRIMARY KEY(iteration_number,interval_id)
);
CREATE TABLE record_lineage (
  child_record_id uuid PRIMARY KEY REFERENCES source_records,
  parent_record_id uuid NOT NULL REFERENCES source_records,
  baseline_record_id uuid NOT NULL REFERENCES source_records,
  method text NOT NULL
);
CREATE TABLE well_audits (
  audit_id uuid PRIMARY KEY REFERENCES source_records,
  iteration_number integer NOT NULL REFERENCES iterations,
  well_id text NOT NULL REFERENCES wells,
  numeric_category text NOT NULL,
  ground_height_category text NOT NULL,
  UNIQUE(iteration_number,well_id)
);
CREATE TABLE findings (
  finding_id text PRIMARY KEY,
  audit_record_id uuid NOT NULL REFERENCES source_records,
  iteration_number integer NOT NULL REFERENCES iterations,
  well_id text NOT NULL REFERENCES wells,
  affected_record_id uuid NOT NULL REFERENCES source_records,
  interval_id uuid REFERENCES intervals,
  issue_code text NOT NULL,
  description text NOT NULL,
  review_status text NOT NULL DEFAULT 'open'
);
CREATE INDEX findings_well_idx ON findings(well_id);
CREATE TABLE finding_events (
  event_id uuid PRIMARY KEY,
  finding_id text NOT NULL REFERENCES findings,
  iteration_number integer NOT NULL REFERENCES iterations,
  status text NOT NULL,
  explanation text NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE ground_height_candidates (
  candidate_id uuid PRIMARY KEY REFERENCES source_records,
  well_id text NOT NULL REFERENCES wells,
  affected_record_id uuid NOT NULL REFERENCES source_records,
  interval_id uuid NOT NULL REFERENCES intervals,
  endpoint text NOT NULL,
  candidate_height_ft numeric,
  adoption_status text NOT NULL DEFAULT 'candidate_not_adopted'
);
CREATE TABLE ground_height_sources (
  height_source_id uuid PRIMARY KEY REFERENCES source_records,
  gw_site_id text NOT NULL,
  height_ft numeric,
  vertical_reference_raw text,
  metadata_source_id text NOT NULL REFERENCES source_files,
  page_source_id text NOT NULL REFERENCES source_files
);
CREATE TABLE well_height_links (
  well_id text NOT NULL REFERENCES wells,
  height_source_id uuid NOT NULL REFERENCES ground_height_sources,
  coordinate_match boolean,
  adoption_status text NOT NULL DEFAULT 'linked_site_evidence_not_adopted',
  PRIMARY KEY(well_id,height_source_id)
);
CREATE TABLE duplicate_wells (
  removed_well_id text PRIMARY KEY REFERENCES wells,
  representative_well_id text NOT NULL REFERENCES wells,
  distance_m numeric NOT NULL,
  audit_record_id uuid NOT NULL REFERENCES source_records
);
CREATE TABLE duplicate_intervals (
  removed_interval_id uuid PRIMARY KEY REFERENCES intervals,
  representative_interval_id uuid NOT NULL REFERENCES intervals,
  audit_record_id uuid NOT NULL REFERENCES source_records
);
CREATE TABLE decisions (
  decision_id text PRIMARY KEY,
  iteration_number integer NOT NULL REFERENCES iterations,
  source_id text REFERENCES source_files,
  details jsonb NOT NULL
);
CREATE TABLE changes (
  change_id uuid PRIMARY KEY,
  iteration_number integer NOT NULL REFERENCES iterations,
  well_id text NOT NULL REFERENCES wells,
  interval_id uuid REFERENCES intervals,
  decision_id text NOT NULL REFERENCES decisions,
  field_name text NOT NULL,
  original_value jsonb,
  accepted_value jsonb,
  reason text NOT NULL
);
CREATE VIEW working_wells AS
SELECT w.well_id,v.record_id,v.latitude,v.longitude,v.completed_depth_ft,v.location,
       v.horizontal_reference_status,r.raw_values,a.numeric_category,a.ground_height_category,
       ar.raw_values AS audit_values
FROM well_membership w JOIN well_versions v ON v.record_id=w.version_record_id
JOIN source_records r ON r.record_id=v.record_id
LEFT JOIN well_audits a ON a.well_id=w.well_id AND a.iteration_number=3
LEFT JOIN source_records ar ON ar.record_id=a.audit_id
WHERE w.iteration_number=(SELECT max(iteration_number) FROM iterations WHERE is_data_release) AND w.state='working';
CREATE VIEW working_intervals AS
SELECT i.interval_id,i.well_id,i.kind,v.record_id,v.top_depth_ft,v.bottom_depth_ft,
       v.top_elevation_ft,v.bottom_elevation_ft,v.thickness_ft,v.strat_unit,v.material_raw,r.raw_values
FROM interval_membership m JOIN intervals i USING(interval_id)
JOIN interval_versions v ON v.record_id=m.version_record_id JOIN source_records r ON r.record_id=v.record_id
WHERE m.iteration_number=(SELECT max(iteration_number) FROM iterations WHERE is_data_release) AND m.state='working';
CREATE VIEW arcgis_wells AS
SELECT well_id,latitude,longitude,completed_depth_ft,numeric_category,ground_height_category,
       horizontal_reference_status,location FROM working_wells;
CREATE FUNCTION protect_history() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Historical records are append-only; create a new revision and iteration instead'; END $$;
DO $$ DECLARE name text; BEGIN
FOREACH name IN ARRAY ARRAY['source_files','source_records','wells','well_versions','intervals','interval_versions','record_lineage','well_membership','interval_membership','well_audits','ground_height_candidates','ground_height_sources','well_height_links','duplicate_wells','duplicate_intervals','decisions','changes','findings','finding_events']
LOOP EXECUTE format('CREATE TRIGGER preserve_history BEFORE UPDATE OR DELETE ON boardman.%I FOR EACH ROW EXECUTE FUNCTION boardman.protect_history()',name); END LOOP;
END $$;
COMMIT;
