# GitHub → AWS OIDC Trust Setup

## Inputs & Assumptions
- **AWS Account ID**: `513348493870` (ap-northeast-2).
- **GitHub Repository**: `Softbank-mango/deplight-platform`.
- **Default subject pattern**: `repo:Softbank-mango/deplight-platform:ref:refs/heads/*`.
- **Audience**: `sts.amazonaws.com`.
- **Thumbprint**: `6938fd4d98bab03faadb97b34396831e3780aea1` (GitHub Actions root cert as of 2025-11-04).

## Terraform Module
- Module path: `infrastructure/modules/iam-github-oidc`.
- Resources:
  - `aws_iam_openid_connect_provider` for `https://token.actions.githubusercontent.com`.
  - `aws_iam_role` with trust policy above.
  - Inline policy granting `sts:GetCallerIdentity` (expand later tasks as needed).
- Inputs: `github_org`, `github_repo`, `role_name`, optional `allowed_subjects`, `github_oidc_audience`, `max_session_duration`.
- Outputs: `role_arn`, `oidc_provider_arn`.

## Validation Checklist
- `terraform plan` (run from temporary root: `infrastructure/tmp-github-oidc`) confirms provider + role creation.
- GitHub Actions smoke workflows:
  - `.github/workflows/oidc-smoke.yml` (T-01 validation) — manual dispatch returns the IAM role ARN via `aws sts get-caller-identity`.
  - `.github/workflows/oidc-credentials.yml` (T-02 verification) — manual dispatch ensures the deployment pipeline can assume the role using the `AWS_GITHUB_OIDC_ROLE` secret.
- Workflow success logs must show the IAM role ARN returned by STS.

## Terraform Backend & Environment Notes
- Terraform state is stored in S3 bucket `deplight-platform-tf-state`, key `global/terraform.tfstate`, with locking via DynamoDB table `deplight-platform-tf-locks` (region `ap-northeast-2`).
- Run `terraform init -migrate-state` once after cloning to connect to the remote backend.
- Use per-environment tfvars:
  - Dev: `terraform plan -var-file=environments/dev.tfvars`
  - Prod: `terraform plan -var-file=environments/prod.tfvars`
- Additional overrides (from AI analyzer or CI) can be supplied via extra tfvars or `-var` flags; these supersede the default values.

## Maintenance Notes
- If repo naming or environments change, update `allowed_subjects` and re-run plan.
- Monitor GitHub’s OIDC thumbprint; if it rotates, update Terraform variable and re-apply.
- Extend IAM permissions once deployment tasks (T-02/T-05) define the required AWS services.
