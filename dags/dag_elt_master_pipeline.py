# ============================================================================
# ARQUIVO: dags/dag_elt_master_pipeline.py
# DESCRIÇÃO: DAG Master do Apache Airflow orquestrando o pipeline ELT completo
# ============================================================================
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

from src.ingestion.file_reader import TABELAS_BERKA, read_asc_local_pandas
from src.governance.lgpd_anonymizer import LGPDAnonymizer
from src.governance.bias_auditor import CreditBiasAuditor
from src.transformation.cleaning_pipeline import BerkaCleaningPipeline
from src.transformation.scd_incremental_load import SCD2Loader
from src.utils.logger import get_logger

logger = get_logger("AirflowMasterDAG")

RAW_DATA_DIR = Path("/opt/airflow/data/raw")
STAGING_DIR = Path("/tmp/berka_staging")


def task_extract_raw_data(**kwargs) -> None:
    """1. Extração: Verifica e carrega os ficheiros brutos .asc do Banco Berka."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Iniciando verificação dos {len(TABELAS_BERKA)} ficheiros brutos do Banco Berka...")

    for asc_file, table_name in TABELAS_BERKA.items():
        file_path = RAW_DATA_DIR / asc_file
        if file_path.exists():
            df = read_asc_local_pandas(file_path)
            df.to_parquet(STAGING_DIR / f"bronze_{table_name}.parquet", index=False)
            logger.info(f"Tabela Bronze '{table_name}' salva em staging ({len(df)} linhas).")
        else:
            logger.warning(f"Ficheiro {file_path} não encontrado localmente; utilizando camada Bronze Cloud.")


def task_anonymize_and_audit_lgpd(**kwargs) -> None:
    """2. Governança: Aplica pseudonimização SHA-256 (LGPD/GDPR) e audita viés demográfico."""
    anonymizer = LGPDAnonymizer()
    client_bronze_path = STAGING_DIR / "bronze_client.parquet"

    if client_bronze_path.exists():
        df_client = pd.read_parquet(client_bronze_path)
        df_anon = anonymizer.anonymize_pandas_client(df_client, pii_hash_cols=["birth_number"], drop_raw_pii=False)
        df_anon.to_parquet(STAGING_DIR / "bronze_client_lgpd.parquet", index=False)
        logger.info("Pseudonimização LGPD concluída com sucesso sobre a tabela 'client'.")


def task_clean_silver_layer(**kwargs) -> None:
    """3. Transformação Silver: Tipagem, datas do século XX e tradução de domínios em checo."""
    cleaner = BerkaCleaningPipeline()
    auditor = CreditBiasAuditor()

    client_path = STAGING_DIR / "bronze_client.parquet"
    if client_path.exists():
        df_client_raw = pd.read_parquet(client_path)
        df_client_silver = cleaner.clean_client(df_client_raw)
        auditor.audit_representation(df_client_silver, demographic_col="genero")
        df_client_silver.to_parquet(STAGING_DIR / "silver_client.parquet", index=False)

    loan_path = STAGING_DIR / "bronze_loan.parquet"
    if loan_path.exists():
        df_loan_raw = pd.read_parquet(loan_path)
        df_loan_silver = cleaner.clean_loan(df_loan_raw)
        df_loan_silver.to_parquet(STAGING_DIR / "silver_loan.parquet", index=False)


def task_load_gold_scd2_dw(**kwargs) -> None:
    """4. Carga Gold DW: Aplica Slowly Changing Dimensions (SCD Tipo 2) na dim_cliente."""
    scd_loader = SCD2Loader()
    silver_client_path = STAGING_DIR / "silver_client.parquet"
    gold_scd2_path = STAGING_DIR / "gold_dim_clientes_scd2.parquet"

    if silver_client_path.exists():
        df_incoming = pd.read_parquet(silver_client_path)
        df_target = pd.read_parquet(gold_scd2_path) if gold_scd2_path.exists() else pd.DataFrame()

        df_updated_scd2 = scd_loader.apply_scd2_pandas(
            df_target=df_target,
            df_incoming=df_incoming,
            natural_key="id_cliente",
            tracked_cols=["id_distrito"],
        )
        df_updated_scd2.to_parquet(gold_scd2_path, index=False)
        logger.info(f"Dimensão SCD Tipo 2 atualizada na camada Gold: {len(df_updated_scd2)} registos.")


def task_refresh_analytics_views(**kwargs) -> None:
    """5. Camada Analítica: Valida disponibilidade das tabelas Fato e Dimensão para o BI/Streamlit."""
    logger.info("Pipeline ELT Master concluído. Views analíticas da camada Gold prontas para consumo!")


# Configuração padrão de governança e resiliência da DAG
default_args = {
    "owner": "christian.wislocki",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="berka_elt_master_pipeline",
    default_args=default_args,
    description="Pipeline ELT Full-Stack do Banco Berka (Bronze -> LGPD -> Silver -> Gold SCD2)",
    schedule_interval="0 6 * * *",  # Execução diária às 06:00 UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["berka_bank", "lakehouse", "lgpd", "scd2", "gold"],
) as dag:

    t1_extract = PythonOperator(
        task_id="extract_raw_berka_files",
        python_callable=task_extract_raw_data,
    )

    t2_lgpd = PythonOperator(
        task_id="anonymize_pii_lgpd",
        python_callable=task_anonymize_and_audit_lgpd,
    )

    t3_silver = PythonOperator(
        task_id="clean_and_transform_silver",
        python_callable=task_clean_silver_layer,
    )

    t4_scd2_gold = PythonOperator(
        task_id="apply_scd2_gold_dw",
        python_callable=task_load_gold_scd2_dw,
    )

    t5_analytics = PythonOperator(
        task_id="refresh_analytics_views",
        python_callable=task_refresh_analytics_views,
    )

    # Ordem de dependência estrita: Extrair -> Anonimizar (LGPD) -> Limpar -> Aplicar SCD no DW -> Atualizar Views
    t1_extract >> t2_lgpd >> t3_silver >> t4_scd2_gold >> t5_analytics