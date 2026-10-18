# ============================================================================
# Parâmetros dinâmicos para provisionamento na AWS
# ============================================================================

variable "aws_region" {
  description = "Região da AWS (alinhada ao metastore us-east-2 do Databricks)"
  type        = string
  default     = "us-east-2"
}

variable "project_name" {
  description = "Prefixo padrão para nomenclatura dos recursos Cloud"
  type        = string
  default     = "berka-bank-lakehouse"
}

variable "environment" {
  description = "Ambiente de execução (dev, staging, prod)"
  type        = string
  default     = "prod"
}