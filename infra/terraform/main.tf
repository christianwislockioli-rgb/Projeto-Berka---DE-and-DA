# ============================================================================
# Provisionamento da Arquitetura Medalhão (S3 Bronze/Silver/Gold + Glue + Athena)
# ============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Domain      = "Financial-Analytics-Berka"
    }
  }
}

# 1. Buckets Amazon S3 para a Arquitetura Medalhão (Bronze, Silver, Gold) e Athena
locals {
  medallion_layers = toset(["bronze", "silver", "gold", "athena-query-results"])
}

resource "aws_s3_bucket" "medallion_buckets" {
  for_each = local.medallion_layers
  bucket   = "${var.project_name}-${each.key}-${var.environment}"
}

# Bloqueio de acesso público em todos os buckets por segurança e conformidade LGPD
resource "aws_s3_bucket_public_access_block" "medallion_security" {
  for_each = aws_s3_bucket.medallion_buckets
  bucket   = each.value.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Criptografia AES-256 em repouso (Server-Side Encryption)
resource "aws_s3_bucket_server_side_encryption_configuration" "medallion_encryption" {
  for_each = aws_s3_bucket.medallion_buckets
  bucket   = each.value.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 2. Catálogo de Dados no AWS Glue (Equivalente ao schema portfolio no Unity Catalog)
resource "aws_glue_catalog_database" "berka_catalog" {
  name        = "portfolio_berka_${var.environment}"
  description = "Catálogo de metadados do Lakehouse Berka (Camadas Bronze, Silver e Gold)"
}

# 3. Workgroup do Amazon Athena para consultas SQL Serverless na camada Gold
resource "aws_athena_workgroup" "analytics_wg" {
  name = "${var.project_name}_wg_${var.environment}"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.medallion_buckets["athena-query-results"].bucket}/output/"
    }
  }
}