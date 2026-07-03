---
paths:
  - "**/*.tf"
  - "**/*.tfvars"
  - "terraform/**/*"
---

# Terraform Conventions

## Module structure
- All Terraform code lives in terraform/ directory.
- Environment configs: terraform/environments/{dev,staging,prod}/
- Reusable modules: terraform/modules/<module-name>/

## Variable naming
- Use snake_case for all variable names.
- Boolean variables: prefix with enable_ or is_ (e.g., enable_deletion_protection)
- Sensitive variables: suffix with _secret (e.g., db_password_secret)
  Mark sensitive=true in variable definition.

## Resource naming
- Pattern: <project>-<env>-<resource-type>-<name>
  Examples: billing-prod-rds-primary, billing-dev-sqs-refunds

## Before modifying any Terraform
1. Run: terraform plan -out=tfplan
2. Review ALL changes — especially: destroy operations, security group changes
3. For PROD: always get a second review before applying

## Safety rules
- NEVER use -auto-approve in production.
- Deletion protection MUST be enabled for: RDS instances, DynamoDB tables, S3 buckets.
- State file is in remote backend (S3 + DynamoDB lock) — never run terraform locally for prod.
