data "aws_caller_identity" "current" {}

locals {
  repo_full_name = "${var.github_org}/${var.github_repo}"
}

# Trust policy
data "aws_iam_policy_document" "gha_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [for b in var.allowed_branches : "repo:${local.repo_full_name}:${b}"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "gha_deploy_dev" {
  name               = "${var.project}-${var.env}-gha-deploy"
  assume_role_policy = data.aws_iam_policy_document.gha_trust.json
  tags               = var.tags
}

# Admin in dev for rapid prototyping
resource "aws_iam_role_policy_attachment" "admin_attach" {
  role       = aws_iam_role.gha_deploy_dev.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
