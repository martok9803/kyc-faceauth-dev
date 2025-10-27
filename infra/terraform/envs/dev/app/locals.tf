locals {
  name_prefix    = "${var.project}-${var.env}"
  uploads_bucket = "${local.name_prefix}-uploads"
  ddb_sessions   = "${local.name_prefix}-sessions"
  log_retention  = 14
}
