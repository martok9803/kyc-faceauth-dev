data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "${local.name_prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "cwlogs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "s3_access" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.uploads.arn}/*"]
  }
}

resource "aws_iam_policy" "s3_access" {
  name   = "${local.name_prefix}-s3-access"
  policy = data.aws_iam_policy_document.s3_access.json
}

resource "aws_iam_role_policy_attachment" "s3_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

data "aws_iam_policy_document" "ddb_access" {
  statement {
    actions   = ["dynamodb:PutItem", "dynamodb:GetItem"]
    resources = [aws_dynamodb_table.sessions.arn]
  }
}

resource "aws_iam_policy" "ddb_access" {
  name   = "${local.name_prefix}-ddb-access"
  policy = data.aws_iam_policy_document.ddb_access.json
}

resource "aws_iam_role_policy_attachment" "ddb_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.ddb_access.arn
}

data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn_role" {
  name               = "${local.name_prefix}-sfn-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

data "aws_iam_policy_document" "sfn_min" {
  statement {
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "sfn_min" {
  name   = "${local.name_prefix}-sfn-min"
  policy = data.aws_iam_policy_document.sfn_min.json
}

resource "aws_iam_role_policy_attachment" "sfn_min_attach" {
  role       = aws_iam_role.sfn_role.name
  policy_arn = aws_iam_policy.sfn_min.arn
}

data "aws_iam_policy_document" "sfn_start" {
  statement {
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.pipeline.arn]
  }
}
resource "aws_iam_policy" "sfn_start" {
  name   = "${local.name_prefix}-sfn-start"
  policy = data.aws_iam_policy_document.sfn_start.json
}
resource "aws_iam_role_policy_attachment" "sfn_start_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.sfn_start.arn
}

data "aws_iam_policy_document" "rekognition_liveness" {
  statement {
    actions   = ["rekognition:CreateFaceLivenessSession","rekognition:GetFaceLivenessSessionResults"]
    resources = ["*"]
  }
}
resource "aws_iam_policy" "rekognition_liveness" {
  name   = "${local.name_prefix}-rekognition-liveness"
  policy = data.aws_iam_policy_document.rekognition_liveness.json
}
resource "aws_iam_role_policy_attachment" "rekognition_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.rekognition_liveness.arn
}
