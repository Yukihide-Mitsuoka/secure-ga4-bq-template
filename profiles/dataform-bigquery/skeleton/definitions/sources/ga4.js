// Google-created GA4 export (daily events_* shards). Read-only external source:
// private exports are locked down by dataset IAM (requirements 3.3), while public
// verification data remains Google-managed. Column-level controls do NOT apply here.
// The wildcard name resolves because ref() renders a backtick-quoted table path.
declare({
  database: dataform.projectConfig.vars.ga4_export_project,
  schema: dataform.projectConfig.vars.ga4_export_dataset,
  name: "events_*",
});
