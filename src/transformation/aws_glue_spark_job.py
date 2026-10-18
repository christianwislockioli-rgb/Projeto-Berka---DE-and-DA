# ============================================================================
# DESCRIÇÃO: Job PySpark Distribuído para AWS Glue / Lakehouse (Bronze -> Silver -> Gold)
# ============================================================================
import sys
from pyspark.sql import SparkSession
import pyspark.sql.functions as F


def run_lakehouse_spark_job(
    spark: SparkSession,
    s3_bronze_path: str = "s3://berka-bank-lakehouse-bronze-prod",
    s3_silver_path: str = "s3://berka-bank-lakehouse-silver-prod",
    s3_gold_path: str = "s3://berka-bank-lakehouse-gold-prod",
) -> None:
    """
    Processa os ficheiros massivos do Banco Berka (incluindo o 1,05 milhão de transações)
    em PySpark distribuído e grava em formato Parquet/Delta otimizado na camada Gold.
    """
    # 1. Leitura distribuída da camada Bronze (trans.asc e loan.asc)
    df_trans_raw = (
        spark.read.option("header", "true")
        .option("inferSchema", "true")
        .option("sep", ";")
        .csv(f"{s3_bronze_path}/trans.asc")
    )

    # 2. Transformação Silver: Tipagem, Datas do Século XX e Tradução de Regras
    df_trans_silver = (
        df_trans_raw.select(
            F.col("trans_id").cast("int").alias("id_transacao"),
            F.col("account_id").cast("string").alias("id_conta"),
            F.to_date(F.concat(F.lit("19"), F.lpad(F.col("date").cast("string"), 6, "0")), "yyyyMMdd").alias("data_transacao"),
            F.when(F.col("type") == "PRIJEM", "Credito")
             .when(F.col("type") == "VYDAJ", "Debito")
             .otherwise("Saque")
             .alias("tipo_transacao"),
            F.col("operation").alias("operacao"),
            F.col("amount").cast("double").alias("valor"),
            F.col("balance").cast("double").alias("saldo"),
            F.col("k_symbol").alias("simbolo_k"),
            F.col("bank").alias("banco_parceiro"),
            # Pseudonimização SHA-256 da conta de terceiros (Conformidade LGPD)
            F.sha2(F.col("account").cast("string"), 256).alias("conta_parceiro_hash"),
        )
        .withColumn("data_processamento_silver", F.current_timestamp())
    )

    df_trans_silver.write.mode("overwrite").parquet(f"{s3_silver_path}/fato_transacao")

    # 3. Escrita na Camada Gold (Remove metadados técnicos de processamento)
    df_trans_gold = df_trans_silver.drop("data_processamento_silver")
    df_trans_gold.write.mode("overwrite").parquet(f"{s3_gold_path}/fato_transacoes")


if __name__ == "__main__":
    spark_session = (
        SparkSession.builder.appName("BerkaBank_AWS_Glue_Lakehouse_Job")
        .getOrCreate()
    )
    # Permite passagem de caminhos S3 via argumentos de execução do AWS Glue
    if len(sys.argv) >= 4:
        run_lakehouse_spark_job(spark_session, sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Sessão PySpark inicializada. Pronto para execução no cluster AWS Glue/Databricks.")