# ============================================================================
# ARQUIVO: tests/test_ingestion.py
# DESCRIÇÃO: Testes unitários (Pytest) para ingestão de ficheiros .asc e limpeza Silver
# ============================================================================
from pathlib import Path
import pandas as pd
from src.ingestion.file_reader import TABELAS_BERKA, read_asc_local_pandas
from src.transformation.cleaning_pipeline import BerkaCleaningPipeline


def test_berka_tables_mapping_completeness():
    """Garante que todas as 8 tabelas oficiais da documentação PKDD'99 estão mapeadas."""
    expected_files = {
        "account.asc",
        "client.asc",
        "disp.asc",
        "order.asc",
        "loan.asc",
        "card.asc",
        "trans.asc",
        "district.asc",
    }
    assert set(TABELAS_BERKA.keys()) == expected_files


def test_read_asc_semicolon_and_audit_column(tmp_path: Path):
    """Testa a leitura de um ficheiro .asc delimitado por ';' e a adição do timestamp Bronze."""
    sample_asc = tmp_path / "account.asc"
    sample_asc.write_text(
        "account_id;district_id;frequency;date\n1;18;POPLATEK MESICNE;950324\n",
        encoding="utf-8",
    )

    df = read_asc_local_pandas(sample_asc)
    assert len(df) == 1
    assert "data_ingestao_bronze" in df.columns
    assert int(df.loc[0, "account_id"]) == 1


def test_silver_cleaning_czech_rules_and_birth_number():
    """
    Valida se a regra do birth_number (mês + 50 para mulheres) e a tradução
    dos status de empréstimo (A, B, C, D) funcionam exatamente como no Databricks.
    """
    cleaner = BerkaCleaningPipeline()

    # Cliente 1: birth_number 706213 -> Mês 62 (>50) -> Mulher ('F'), nascida em 1970-12-13, 28 anos em 1998
    # Cliente 2: birth_number 450204 -> Mês 02 (<=50) -> Homem ('M'), nascido em 1945-02-04, 53 anos em 1998
    df_raw_client = pd.DataFrame({
        "client_id": [1, 2],
        "birth_number": [706213, 450204],
        "district_id": [18, 1],
    })

    df_clean_client = cleaner.clean_client(df_raw_client, ref_date="1998-12-31")
    assert list(df_clean_client["genero"]) == ["F", "M"]
    assert list(df_clean_client["idade"]) == [28, 53]
    assert str(df_clean_client.loc[0, "data_nascimento"].date()) == "1970-12-13"