-- Typed unnest of the GA4 export (FR-1.3): promote the event_params keys the marts
-- need into real columns, so the mart layer can attach policy tags to them. Which
-- keys to promote is an engagement parameter; unpromoted params stay nested here,
-- protected by dataset IAM only.
with source as (

    select *
    from {{ source('ga4', 'events') }}

),

renamed as (

    -- simple references first, calculations after (SQLFluff ST06)
    select
        event_name,
        user_id,
        user_pseudo_id,
        geo.city as geo_city,
        device.category as device_category,
        traffic_source.source as traffic_source,
        parse_date('%Y%m%d', event_date) as event_date,
        timestamp_micros(event_timestamp) as event_ts,
        (
            select ep.value.string_value
            from unnest(event_params) as ep
            where ep.key = 'page_location'
        ) as page_location
    from source

)

select *
from renamed
