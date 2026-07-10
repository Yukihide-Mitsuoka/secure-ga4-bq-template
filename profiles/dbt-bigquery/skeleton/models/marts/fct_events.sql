-- Exemplar mart (rail FR-2): every governance control is declared in config, none
-- retrofitted by hand — partitioning, clustering, mandatory partition filter
-- (cost checkpoints #8/#9), and column policy tags (in _marts__models.yml).
{{
    config(
        materialized='table',
        partition_by={'field': 'event_date', 'data_type': 'date'},
        cluster_by=['event_name'],
        require_partition_filter=true
    )
}}

select
    event_date,
    event_ts,
    event_name,
    user_id,
    user_pseudo_id,
    geo_city,
    device_category,
    traffic_source,
    page_location
from {{ ref('stg_ga4__events') }}
