resource "aws_kms_key" "app" {
  description             = "${local.name_prefix} app key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}
