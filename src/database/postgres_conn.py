# ============================================================================
# DESCRIÇÃO: Abstração de conexão PostgreSQL via SQLAlchemy (ORM) e Psycopg2
# ============================================================================
import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from src.utils.logger import get_logger

logger = get_logger("PostgresConnector")

class PostgresConnector:
    def __init__(self):
        self.user = os.getenv("POSTGRES_USER", "berka_admin")
        self.password = os.getenv("POSTGRES_PASSWORD", "changeme_secret_password")
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        self.db = os.getenv("POSTGRES_DB", "berka_oltp")
        self.connection_url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    def get_engine(self) -> Engine:
        """Retorna a Engine do SQLAlchemy para operações ORM e Pandas."""
        return create_engine(self.connection_url, pool_pre_ping=True)

    def bulk_insert_dataframe(self, df: pd.DataFrame, table_name: str, page_size: int = 5000) -> None:
        """
        Realiza inserção massiva em lote (Bulk Insert) via Psycopg2 nativo.
        Ideal para carregar o 1,05 milhão de registros da tabela 'trans'.
        """
        if df.empty:
            logger.warning(f"DataFrame vazio. Nenhuma linha inserida em '{table_name}'.")
            return

        columns = ",".join(df.columns)
        query = f"INSERT INTO {table_name} ({columns}) VALUES %s ON CONFLICT DO NOTHING"
        values = [tuple(x) for x in df.to_numpy()]

        conn = None
        try:
            conn = psycopg2.connect(
                dbname=self.db, user=self.user, password=self.password, host=self.host, port=self.port
            )
            with conn.cursor() as cur:
                execute_values(cur, query, values, page_size=page_size)
            conn.commit()
            logger.info(f"Sucesso: {len(df)} registros inseridos em lote na tabela '{table_name}'.")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro no Bulk Insert da tabela '{table_name}': {e}")
            raise
        finally:
            if conn:
                conn.close()