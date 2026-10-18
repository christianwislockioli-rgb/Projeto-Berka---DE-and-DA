# ============================================================================
# Retorno dos identificadores e nomes dos recursos criados na AWS
# ============================================================================

output "s3_medallion_buckets" {
  description = "Nomes dos buckets S3 provisionados para a Arquitetura Medalhão"
  value       = { for k, b in aws_s3_bucket.medallion_buckets : k => b.bucket }
}

output "glue_catalog_database_name" {
  description = "Nome do banco de dados criado no AWS Glue Data Catalog"
  value       = aws_glue_catalog_database.berka_catalog.name
}

output "athena_workgroup_name" {
  description = "Nome do Workgroup do Amazon Athena para execução de queries analíticas"
  value       = aws_athena_workgroup.analytics_wg.name
}