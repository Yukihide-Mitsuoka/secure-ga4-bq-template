#!/usr/bin/env bash
# Seed the FR-8 pseudo-sensitive verification data: a fake GA4 export shard that
# exercises every catalog mechanism without any production data.
#
# Why a SQL script and not a dbt seed: CSV seeds cannot express the GA4 export's
# nested shape (event_params ARRAY<STRUCT>, geo/device/traffic_source STRUCTs),
# and the staging exemplar reads exactly that shape (FR-1.3 typed unnest).
#
# FR-8 coverage map (requirements-secure-asset.md):
#   high    user_id (pseudo member ids), email planted in event_params values
#   medium  user_pseudo_id, geo.city
#   unnest  page_location / page_referrer keys exist for typed promotion (FR-1.3)
#   A+      page_location with ?email= query-string PII, phone number in params
#
# Idempotent: CREATE SCHEMA IF NOT EXISTS + CREATE OR REPLACE TABLE (NFR §6).
# Mutates ONLY the pseudo export dataset passed in — run it against the
# verification project, per-command human approval applies (GR-031).
#
# Usage:
#   scripts/seed-verification-data.sh -p <project> [-d analytics_000000000] \
#       [-l asia-northeast1] [-s YYYYMMDD] [-n]
#   -n = bq dry run: validates the SQL against the API, creates nothing, bills nothing.
#        (The trailing count SELECT is skipped — it reads the table the dry run never creates.)
#
# After seeding, wire the dbt vars (profiles/dbt-bigquery/README.md):
#   ga4_export_project: <project>   ga4_export_dataset: <dataset>
# LOCATION must equal the Terraform var.region (taxonomy/dataset location match).
set -euo pipefail

DATASET="analytics_000000000"
LOCATION="asia-northeast1"
SHARD="$(date -u +%Y%m%d)"
PROJECT=""
DRY_RUN=false

while getopts "p:d:l:s:nh" opt; do
  case "$opt" in
    p) PROJECT="$OPTARG" ;;
    d) DATASET="$OPTARG" ;;
    l) LOCATION="$OPTARG" ;;
    s) SHARD="$OPTARG" ;;
    n) DRY_RUN=true ;;
    h) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "usage: $0 -p <project> [-d dataset] [-l location] [-s YYYYMMDD] [-n]" >&2; exit 2 ;;
  esac
done

[ -n "$PROJECT" ] || { echo "error: -p <project> is required" >&2; exit 2; }
case "$SHARD" in [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;; *) echo "error: -s must be YYYYMMDD" >&2; exit 2 ;; esac
ISO_DATE="${SHARD:0:4}-${SHARD:4:2}-${SHARD:6:2}"

# Row literals are kept free of table references so the -n path can validate the
# exact same SELECT standalone (a dry run cannot see the dataset the real run creates).
ROWS_SQL=$(cat <<SQL
SELECT * FROM UNNEST([
  -- 1) clean logged-in pageview: high(user_id) + medium(pseudo, city) columns populated
  STRUCT(
    '${SHARD}' AS event_date,
    UNIX_MICROS(TIMESTAMP('${ISO_DATE} 09:15:00+00')) AS event_timestamp,
    'page_view' AS event_name,
    'U0001' AS user_id,
    '1111.2222333344' AS user_pseudo_id,
    STRUCT('Tokyo' AS city) AS geo,
    STRUCT('desktop' AS category) AS device,
    STRUCT('google' AS source) AS traffic_source,
    [
      STRUCT('page_location' AS key, STRUCT('https://shop.example.com/items/101' AS string_value, CAST(NULL AS INT64) AS int_value, CAST(NULL AS FLOAT64) AS float_value, CAST(NULL AS FLOAT64) AS double_value) AS value),
      STRUCT('page_referrer', STRUCT('https://www.google.com/', NULL, NULL, NULL)),
      STRUCT('quantity', STRUCT(CAST(NULL AS STRING), 2, NULL, NULL))
    ] AS event_params
  ),
  -- 2) bad instrumentation: raw EMAIL inside event_params values (FR-8 high; A+ value-scan target)
  STRUCT(
    '${SHARD}', UNIX_MICROS(TIMESTAMP('${ISO_DATE} 10:02:00+00')), 'sign_up',
    'U0002', '5555.6666777788',
    STRUCT('Yokohama'), STRUCT('mobile'), STRUCT('newsletter'),
    [
      STRUCT('page_location', STRUCT('https://shop.example.com/register/done', NULL, NULL, NULL)),
      STRUCT('user_email', STRUCT('taro.yamada@example.com', NULL, NULL, NULL))
    ]
  ),
  -- 3) query-string PII in page_location (?email=...) — the GA4-specific A+ demo row
  STRUCT(
    '${SHARD}', UNIX_MICROS(TIMESTAMP('${ISO_DATE} 11:30:00+00')), 'purchase',
    CAST(NULL AS STRING), '9999.0000111122',
    STRUCT('Osaka'), STRUCT('mobile'), STRUCT('email'),
    [
      STRUCT('page_location', STRUCT('https://shop.example.com/thanks?order=550&email=hanako.sato@example.com', NULL, NULL, NULL)),
      STRUCT('page_referrer', STRUCT('https://shop.example.com/checkout', NULL, NULL, NULL))
    ]
  ),
  -- 4) phone number planted in params (A+ periphery)
  STRUCT(
    '${SHARD}', UNIX_MICROS(TIMESTAMP('${ISO_DATE} 13:45:00+00')), 'contact_support',
    'U0003', '3333.4444555566',
    STRUCT('Nagoya'), STRUCT('tablet'), STRUCT('(direct)'),
    [
      STRUCT('page_location', STRUCT('https://shop.example.com/support', NULL, NULL, NULL)),
      STRUCT('support_tel', STRUCT('090-1234-5678', NULL, NULL, NULL))
    ]
  ),
  -- 5) anonymous browse: user_id NULL boundary, pseudo-only identification
  STRUCT(
    '${SHARD}', UNIX_MICROS(TIMESTAMP('${ISO_DATE} 15:20:00+00')), 'page_view',
    CAST(NULL AS STRING), '7777.8888999900',
    STRUCT('Sapporo'), STRUCT('desktop'), STRUCT('twitter'),
    [
      STRUCT('page_location', STRUCT('https://shop.example.com/items/205', NULL, NULL, NULL)),
      STRUCT('page_referrer', STRUCT('https://t.co/abc123', NULL, NULL, NULL))
    ]
  )
])
SQL
)

if "$DRY_RUN"; then
  echo "Dry run: validating row SQL for ${PROJECT}.${DATASET}.events_${SHARD} (${LOCATION}) — nothing is created"
  bq --project_id="$PROJECT" --location="$LOCATION" query \
    --use_legacy_sql=false --dry_run "$ROWS_SQL"
  echo "Dry run OK."
  exit 0
fi

echo "Seeding ${PROJECT}.${DATASET}.events_${SHARD} (${LOCATION})"

bq --project_id="$PROJECT" --location="$LOCATION" query \
  --use_legacy_sql=false --nouse_cache <<SQL
CREATE SCHEMA IF NOT EXISTS \`${PROJECT}.${DATASET}\`
OPTIONS (
  location = '${LOCATION}',
  description = 'FR-8 pseudo GA4 export (verification data, no real PII). Lock down with dataset IAM like a real export.'
);

CREATE OR REPLACE TABLE \`${PROJECT}.${DATASET}.events_${SHARD}\` AS
${ROWS_SQL};

SELECT
  COUNT(*) AS rows_seeded,
  COUNTIF(user_id IS NOT NULL) AS with_user_id,
  COUNTIF(EXISTS(SELECT 1 FROM UNNEST(event_params) ep
                 WHERE REGEXP_CONTAINS(COALESCE(ep.value.string_value, ''),
                                       r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+'))) AS rows_with_planted_email
FROM \`${PROJECT}.${DATASET}.events_${SHARD}\`;
SQL

echo "Done. Wire dbt vars: ga4_export_project=${PROJECT} ga4_export_dataset=${DATASET}"
