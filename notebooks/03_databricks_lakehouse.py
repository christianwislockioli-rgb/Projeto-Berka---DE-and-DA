# Databricks notebook source
# ============================================================================
# DESCRIÇÃO: Pipeline Orquestrado Medalhão no Databricks (Bronze -> Silver -> Gold)
# ============================================================================

# COMMAND ----------
# MAGIC %md
# MAGIC ### 1. Camada Bronze: Ingestão Bruta dos Ficheiros `.asc` (Unity Catalog)

# COMMAND ----------
from pyspark.sql.functions import current_timestamp

spark.sql("CREATE SCHEMA IF NOT EXISTS portfolio.bronze")

schema_destino_uc = "portfolio.bronze"
caminho_base_asc = "/Volumes/portfolio/filestore/tables"

tabelas_para_ingerir = {
    "account.asc": "account",
    "client.asc": "client",
    "disp.asc": "disp",
    "order.asc": "order",
    "loan.asc": "loan",
    "card.asc": "card",
    "trans.asc": "trans",
    "district.asc": "district",
}

for arquivo_asc, nome_tabela in tabelas_para_ingerir.items():
    caminho_completo_origem = f"{caminho_base_asc}/{arquivo_asc}"
    tabela_completa_destino = f"{schema_destino_uc}.{nome_tabela}"

    df_raw = (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "true")
        .option("sep", ";")
        .load(caminho_completo_origem)
    )
    df_bronze = df_raw.withColumn("data_ingestao_bronze", current_timestamp())
    df_bronze.write.format("delta").mode("overwrite").saveAsTable(tabela_completa_destino)
    print(f"Sucesso: Tabela {tabela_completa_destino} registada!")

# COMMAND ----------
# MAGIC %md
# MAGIC ### 2. Camada Silver: Limpeza, Tipagem, Datas e Regras de Negócio

# COMMAND ----------
spark.sql("CREATE SCHEMA IF NOT EXISTS portfolio.silver")

# 2.1. Silver Account (dim_conta)
spark.sql("""
CREATE OR REPLACE TABLE portfolio.silver.dim_conta AS
SELECT 
    CAST(account_id AS STRING) AS id_conta,
    CAST(district_id AS STRING) AS id_distrito,
    CASE 
        WHEN frequency = 'POPLATEK MESICNE' THEN 'Emissao Mensal'
        WHEN frequency = 'POPLATEK TYDNE' THEN 'Emissao Semanal'
        WHEN frequency = 'POPLATEK PO OBRATU' THEN 'Emissao apos Transacao'
        ELSE frequency 
    END AS frequencia,
    TO_DATE(CONCAT('19', LPAD(CAST(date AS STRING), 6, '0')), 'yyyyMMdd') AS data,
    data_ingestao_bronze,
    current_timestamp() AS data_processamento_silver
FROM portfolio.bronze.account
""")

# 2.2. Silver Card (dim_cartao)
spark.sql("""
CREATE OR REPLACE TABLE portfolio.silver.dim_cartao AS
SELECT
    CAST(card_id AS STRING) AS id_cartao,
    CAST(disp_id AS STRING) AS id_disp,
    INITCAP(type) AS tipo_cartao,
    TRY_TO_DATE(CONCAT('19', SUBSTRING(CAST(issued AS STRING), 1, 6)), 'yyyyMMdd') AS data_emissao,
    data_ingestao_bronze,
    current_timestamp() AS data_processamento_silver
FROM portfolio.bronze.card
""")

# 2.3. Silver Client (dim_cliente - Descodificação de birth_number para género e idade)
spark.sql("""
CREATE OR REPLACE TABLE portfolio.silver.dim_cliente AS
WITH preparacao AS (
    SELECT 
        client_id,
        district_id,
        data_ingestao_bronze,
        SUBSTRING(LPAD(CAST(birth_number AS STRING), 6, '0'), 1, 2) AS ano,
        CAST(SUBSTRING(LPAD(CAST(birth_number AS STRING), 6, '0'), 3, 2) AS INT) AS mes,
        SUBSTRING(LPAD(CAST(birth_number AS STRING), 6, '0'), 5, 2) AS dia
    FROM portfolio.bronze.client
),
regras AS (
    SELECT 
        *,
        CASE WHEN mes > 50 THEN 'F' ELSE 'M' END AS genero,
        CASE WHEN mes > 50 THEN mes - 50 ELSE mes END AS mes_limpo
    FROM preparacao
)
SELECT
    CAST(client_id AS STRING) AS id_cliente,
    district_id AS id_distrito,
    genero,
    TO_DATE(CONCAT('19', ano, LPAD(CAST(mes_limpo AS STRING), 2, '0'), dia), 'yyyyMMdd') AS data_nascimento,
    FLOOR(MONTHS_BETWEEN('1998-12-31', TO_DATE(CONCAT('19', ano, LPAD(CAST(mes_limpo AS STRING), 2, '0'), dia), 'yyyyMMdd')) / 12) AS idade,
    data_ingestao_bronze,
    current_timestamp() AS data_processamento_silver
FROM regras
""")

# 2.4. Silver Disposition (dim_Disposicao)
spark.sql("""
CREATE OR REPLACE TABLE portfolio.silver.dim_Disposicao AS
SELECT
    CAST(disp_id AS STRING) AS id_disp,
    CAST(client_id AS STRING) AS id_cliente,
    CAST(account_id AS STRING) AS id_conta,
    CASE WHEN type = 'OWNER' THEN 'Titular' ELSE 'Dependente' END AS tipo_disposicao,
    data_ingestao_bronze,
    current_timestamp() AS data_processamento_silver
FROM portfolio.bronze.disp
""")

# 2.5. Silver District (dim_distrito)
spark.sql("""
CREATE OR REPLACE TABLE portfolio.silver.dim_distrito AS
SELECT
    CAST(A1 AS INT) AS id_distrito,
    CAST(A2 AS STRING) AS nome_distrito,
    CAST(A3 AS STRING) AS regiao,
    CASE WHEN CAST(A10 AS DOUBLE) >= 85.0 OR A3 = 'Prague' THEN 'Metropolitana' ELSE 'Interior' END AS tipo_zona,
    CAST(A4 AS INT) AS habitantes,
    CAST(A10 AS DOUBLE) AS proporcao_urbana,
    CAST(A11 AS DOUBLE) AS salario_medio,
    TRY_CAST(A12 AS DOUBLE) AS taxa_desemprego_95,
    CAST(A13 AS DOUBLE) AS taxa_desemprego_96,
    CAST(A14 AS INT) AS empreendedores_por_1000,
    TRY_CAST(A15 AS INT) AS crimes_95,
    CAST(A16 AS INT) AS crimes_96,
    data_ingestao_bronze,
    current_timestamp() AS data_processamento_silver
FROM portfolio.bronze.district
""")

# 2.6. Silver Loan (fato_emprestimo)
spark.sql("""
CREATE OR REPLACE TABLE portfolio.silver.fato_emprestimo AS
SELECT
    CAST(loan_id AS STRING) AS id_emprestimo,
    CAST(account_id AS STRING) AS id_conta,
    TO_DATE(CONCAT('19', LPAD(CAST(date AS STRING), 6, '0')), 'yyyyMMdd') AS data_emprestimo,
    CAST(amount AS INT) AS valor_emprestimo,
    CAST(duration AS INT) AS duracao,
    CAST(payments AS DOUBLE) AS parcelas,
    CASE
        WHEN status = 'A' THEN 'Encerrado - Regular'
        WHEN status = 'B' THEN 'Encerrado - Inadimplente'
        WHEN status = 'C' THEN 'Ativo - Regular'
        WHEN status = 'D' THEN 'Ativo - Inadimplente'
        ELSE status
    END AS status_emprestimo,
    data_ingestao_bronze,
    current_timestamp() AS data_processamento_silver
FROM portfolio.bronze.loan
""")

# 2.7. Silver Permanent Order (fato_ordem)
spark.sql("""
CREATE OR REPLACE TABLE portfolio.silver.fato_ordem AS
SELECT
    CAST(order_id AS STRING) AS id_ordem,
    CAST(account_id AS STRING) AS id_conta,
    CAST(bank_to AS STRING) AS banco_destino,
    SHA2(CAST(account_to AS STRING), 256) AS conta_destino_hash,
    CAST(amount AS DOUBLE) AS valor_ordem,
    CASE
        WHEN k_symbol = 'POJISTNE' THEN 'Seguro'
        WHEN k_symbol = 'SIPO' THEN 'Despesas Domesticas'
        WHEN k_symbol = 'LEASING' THEN 'Leasing'
        WHEN k_symbol = 'UVER' THEN 'Emprestimo'
        ELSE 'Outros'
    END AS caracterizacao_pagamento,
    data_ingestao_bronze,
    current_timestamp() AS data_processamento_silver
FROM portfolio.bronze.order
""")

# 2.8. Silver Transactions (fato_transacao)
spark.sql("""
CREATE OR REPLACE TABLE portfolio.silver.fato_transacao AS
SELECT
    CAST(trans_id AS INT) AS id_transacao,
    CAST(account_id AS STRING) AS id_conta,
    TO_DATE(CONCAT('19', LPAD(CAST(date AS STRING), 6, '0')), 'yyyyMMdd') AS data_transacao,
    CAST(amount AS DOUBLE) AS valor,
    CAST(balance AS DOUBLE) AS saldo,
    type AS codigo_tipo,
    operation AS codigo_operacao,
    k_symbol AS simbolo_k,
    data_ingestao_bronze,
    current_timestamp() AS data_processamento_silver
FROM portfolio.bronze.trans
""")

# COMMAND ----------
# MAGIC %md
# MAGIC ### 3. Camada Gold: Modelagem Star Schema (Fatos e Dimensões Analíticas)

# COMMAND ----------
spark.sql("CREATE SCHEMA IF NOT EXISTS portfolio.gold")

tabelas_gold = {
    "dim_cliente": "dim_cliente",
    "dim_conta": "dim_conta",
    "dim_cartao": "dim_cartao",
    "dim_distrito": "dim_distrito",
    "dim_Disposicao": "dim_Disposicao",
    "fato_transacoes": "fato_transacao",
    "fato_emprestimos": "fato_emprestimo",
    "fato_ordem": "fato_ordem",
}

for gold_name, silver_name in tabelas_gold.items():
    spark.sql(f"""
        CREATE OR REPLACE TABLE portfolio.gold.{gold_name} AS
        SELECT * EXCEPT (data_ingestao_bronze, data_processamento_silver)
        FROM portfolio.silver.{silver_name}
    """)
    print(f"Tabela Gold criada: portfolio.gold.{gold_name}")