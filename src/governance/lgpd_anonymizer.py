# ============================================================================
# DESCRIÇÃO: Mascaramento, Hash SHA-256 e pseudonimização de PII (LGPD/GDPR)
# ============================================================================
import hashlib
import os
from typing import List, Optional
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("LGPDAnonymizer")


class LGPDAnonymizer:
    """
    Motor de Governança e Privacidade (LGPD / GDPR) para o Lakehouse Berka.
    Suporta execução local (Pandas) e distribuída no Databricks (PySpark).
    """

    def __init__(self, salt: Optional[str] = None):
        # Usa um salt de ambiente para impedir ataques de Rainbow Table sobre CPFs/birth_numbers
        self.salt = salt or os.getenv("LGPD_HASH_SALT", "berka_bank_lgpd_secret_salt_2026")

    def _sha256_value(self, val: object) -> Optional[str]:
        """Converte qualquer valor escalar não nulo em um hash SHA-256 hexadecimal (64 caracteres)."""
        if pd.isna(val) or val is None or str(val).strip() == "":
            return None
        salted = f"{str(val).strip()}{self.salt}".encode("utf-8")
        return hashlib.sha256(salted).hexdigest()

    def anonymize_pandas_client(
        self,
        df: pd.DataFrame,
        pii_hash_cols: Optional[List[str]] = None,
        drop_raw_pii: bool = True,
    ) -> pd.DataFrame:
        """
        Pseudonimiza colunas PII em um DataFrame Pandas (ex: birth_number, CPF, e-mail, conta destino)
        e generaliza a data de nascimento para conformidade com o princípio da minimização (LGPD Art. 6º).
        """
        df_clean = df.copy()
        pii_hash_cols = pii_hash_cols or ["birth_number", "cpf", "email", "account_to", "partner_account"]

        for col in pii_hash_cols:
            if col in df_clean.columns:
                hashed_col_name = f"{col}_sha256" if not drop_raw_pii else col
                logger.info(f"Aplicando pseudonimização SHA-256 na coluna sensível: '{col}'")
                df_clean[hashed_col_name] = df_clean[col].apply(self._sha256_value)

        # Generalização de data_nascimento: mantém apenas o ano e a idade, mascarando dia e mês
        if "data_nascimento" in df_clean.columns:
            logger.info("Generalizando 'data_nascimento' para 'ano_nascimento' (Proteção contra reidentificação).")
            dt_series = pd.to_datetime(df_clean["data_nascimento"], errors="coerce")
            df_clean["ano_nascimento"] = dt_series.dt.year
            if drop_raw_pii:
                df_clean = df_clean.drop(columns=["data_nascimento"])

        return df_clean

    def anonymize_spark_client(self, df_spark, drop_birth_date: bool = True):
        """
        Aplica SHA-256 nativo do PySpark sobre tabelas do Databricks (ex: portfolio.silver.client).
        """
        import pyspark.sql.functions as F

        logger.info("Iniciando anonimização distribuída via PySpark (LGPD/GDPR)...")
        df_out = df_spark

        # Se birth_number ainda existir (ex: passagem Bronze -> Silver), aplica SHA-256
        if "birth_number" in df_out.columns:
            df_out = df_out.withColumn(
                "birth_number",
                F.sha2(F.concat(F.col("birth_number").cast("string"), F.lit(self.salt)), 256),
            )

        # Na passagem Silver -> Gold (dim_cliente), extrai o ano e mascara a data exata de nascimento
        if "data_nascimento" in df_out.columns:
            df_out = df_out.withColumn("ano_nascimento", F.year(F.col("data_nascimento")))
            if drop_birth_date:
                df_out = df_out.drop("data_nascimento")

        # Cria chave pseudonimizada de auditoria para o id_cliente
        if "id_cliente" in df_out.columns:
            df_out = df_out.withColumn(
                "hash_cliente_lgpd",
                F.sha2(F.concat(F.col("id_cliente").cast("string"), F.lit(self.salt)), 256),
            )

        logger.info("Anonimização PySpark concluída com sucesso.")
        return df_out