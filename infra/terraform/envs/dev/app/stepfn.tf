resource "aws_sfn_state_machine" "pipeline" {
  name     = "${local.name_prefix}-pipeline"
  role_arn = aws_iam_role.sfn_role.arn

  definition = jsonencode({
    Comment = "Placeholder pipeline"
    StartAt = "Pass"
    States = {
      Pass = { Type = "Pass", End = true }
    }
  })
}
