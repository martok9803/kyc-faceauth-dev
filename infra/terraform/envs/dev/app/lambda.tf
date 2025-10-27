// Build image in CI and push to ECR; for now we point to :latest placeholder
resource "aws_ecr_repository" "echo" {
  name                 = "${local.name_prefix}-echo"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_lambda_function" "echo" {
  function_name = "${local.name_prefix}-echo"
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.echo.repository_url}:latest"
  timeout       = 10
  memory_size   = 256
  architectures = ["x86_64"]

  environment {
  variables = {
    DDB_TABLE           = aws_dynamodb_table.sessions.name
    BUCKET              = aws_s3_bucket.uploads.bucket
    STATE_MACHINE_ARN   = aws_sfn_state_machine.pipeline.arn
    REKOGNITION_ENABLED = "false"   // false for demo (free)
  }
 }
}
