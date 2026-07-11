// Google-created GA4 export (daily events_* shards). Read-only source, locked down
// by dataset IAM (requirements 3.3); column-level controls do NOT apply here.
// The wildcard name resolves because ref() renders a backtick-quoted table path.
declare({
  database: dataform.projectConfig.vars.ga4_export_project,
  schema: dataform.projectConfig.vars.ga4_export_dataset,
  name: "events_*",
});
