# ============================================================================
# DESCRIÇÃO: Leitura otimizada dos arquivos brutos .asc/.csv do Banco Berka
# ============================================================================
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from typing import Dict
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("BerkaFileReader")

TABELAS_BERKA: Dict[str, str] = {
    "account.asc": "account",
    "client.asc": "client",
    "disp.asc": "disp",
    "order.asc": "order",
    "loan.asc": "loan",
    "card.asc": "card",
    "trans.asc": "trans",
    "district.asc": "district"
}

def ingest_asc_to_databricks_bronze(
    spark_session,
    caminho_base_asc: str = "/Volumes/portfolio/filestore/tables",
    schema_destino_uc: str = "portfolio.bronze"
) -> None:
    """
    Executa a ingestão distribuída via PySpark para a camada Bronze (Delta Lake).
    """
    from pyspark.sql.functions import current_timestamp

    spark_session.sql(f"CREATE SCHEMA IF NOT EXISTS {schema_destino_uc}")

    for arquivo_asc, nome_tabela in TABELAS_BERKA.items():
        caminho_completo = f"{caminho_base_asc}/{arquivo_asc}"
        tabela_destino = f"{schema_destino_uc}.{nome_tabela}"
        
        logger.info(f"Processando: {arquivo_asc} -> Tabela {tabela_destino}...")
        try:
            df_raw = (
                spark_session.read.format("csv")
                .option("header", "true")
                .option("inferSchema", "true")
                .option("sep", ";")
                .load(caminho_completo)
            )
            df_bronze = df_raw.withColumn("data_ingestao_bronze", current_timestamp())
            
            (
                df_bronze.write.format("delta")
                .mode("overwrite")
                .saveAsTable(tabela_destino)
            )
            logger.info(f"Sucesso: Tabela {tabela_destino} registrada na camada Bronze!")
        except Exception as e:
            logger.error(f"Erro ao processar o arquivo {arquivo_asc}: {e}")
            raise

def read_asc_local_pandas(file_path: str | Path) -> pd.DataFrame:
    """
    Lê um arquivo .asc ou .csv bruto localmente usando Pandas otimizado.
    """
    logger.info(f"Lendo arquivo local: {file_path}")
    df = pd.read_csv(file_path, sep=";", low_memory=False)
    df["data_ingestao_bronze"] = pd.Timestamp.now(tz="UTC")
    return df

if __name__ == "__main__":
    print("=== TESTANDO O LEITOR BERKA (LOCAL COM PANDAS) ===")
    
    # Exemplo apontando para um dos arquivos .asc caso você os tenha baixados localmente
    caminho_exemplo = Path("data/raw/account.asc")
    
    if caminho_exemplo.exists():
        df_amostra = read_asc_local_pandas(caminho_exemplo)
        print("Arquivo lido com sucesso!")
        print(df_amostra.head())
    else:
        print(f"Arquivo de exemplo não encontrado em '{caminho_exemplo}'.")
        print("Coloque os ficheiros .asc na pasta de dados local se quiser testar a leitura via Pandas.")
        print("As funções de ingestão via PySpark (Databricks) estão carregadas e prontas para uso.")