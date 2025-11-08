terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  github_oidc_thumbprints = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
  default_subject_pattern = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/*"
  subject_patterns        = length(var.allowed_subjects) > 0 ? var.allowed_subjects : [local.default_subject_pattern]
}

resource "aws_iam_openid_connect_provider" "github" {
  client_id_list  = [var.github_oidc_audience]
  thumbprint_list = local.github_oidc_thumbprints
  url             = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    sid     = "GitHubActionsOIDC"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = [var.github_oidc_audience]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.subject_patterns
    }

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name                 = var.role_name
  description          = "GitHub Actions OIDC role for ${var.github_org}/${var.github_repo}"
  assume_role_policy   = data.aws_iam_policy_document.assume_role.json
  max_session_duration = var.max_session_duration
}

data "aws_iam_policy_document" "base_permissions" {
  statement {
    sid       = "DryRunCallerIdentity"
    actions   = ["sts:GetCallerIdentity"]
    resources = ["*"]
  }

  statement {
    sid = "ECRPush"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
      "ecr:DescribeRepositories"
    ]
    resources = ["*"]
  }

  statement {
    sid = "TerraformRead"
    actions = [
      "ecs:DescribeClusters",
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:ListClusters",
      "ecs:ListServices",
      "codedeploy:GetDeployment",
      "codedeploy:ListDeployments",
      "cloudwatch:ListDashboards",
      "cloudwatch:DescribeAlarms",
      "logs:DescribeLogGroups"
    ]
    resources = ["*"]
  }

  statement {
    sid = "TerraformWrite"
    actions = [
      "ecs:RegisterTaskDefinition",
      "codedeploy:CreateDeployment",
      "codedeploy:RegisterApplicationRevision",
      "cloudwatch:PutDashboard",
      "cloudwatch:PutMetricAlarm",
      "logs:PutRetentionPolicy"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "base" {
  name        = "${var.role_name}-base"
  description = "Base permissions for GitHub Actions dry-run validation"
  policy      = data.aws_iam_policy_document.base_permissions.json
}

resource "aws_iam_role_policy_attachment" "base" {
  role       = aws_iam_role.github_actions.name
  policy_arn = aws_iam_policy.base.arn
}
