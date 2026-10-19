# ============================================================================
# ARQUIVO: tests/test_scd_logic.py
# DESCRIÇÃO: Testes unitários (Pytest) para a lógica de Carga Incremental SCD Tipo 2
# ============================================================================
import pandas as pd
from src.transformation.scd_incremental_load import SCD2Loader


def test_scd2_initial_load_and_historical_versioning():
    """
    Simula duas cargas na dimensão de clientes:
    - Carga 1: Clientes '1' (distrito 18) e '2' (distrito 1) entram ativos.
    - Carga 2: Cliente '1' muda-se para o distrito 54 (Brno) e entra um novo Cliente '3'.
    Verifica se o Cliente '1' fica com 2 linhas (1 inativa histórica e 1 ativa nova).
    """
    loader = SCD2Loader()

    # 1. Carga Inicial (T0)
    df_t0 = pd.DataFrame({
        "id_cliente": ["1", "2"],
        "id_distrito": [18, 1],
        "genero": ["F", "M"],
        "idade": [28, 53],
    })
    dw_t0 = loader.apply_scd2_pandas(
        df_target=pd.DataFrame(),
        df_incoming=df_t0,
        natural_key="id_cliente",
        tracked_cols=["id_distrito"],
        execution_ts="2026-06-12 01:00:00",
    )

    assert len(dw_t0) == 2
    assert dw_t0["flag_ativo"].all()

    # 2. Carga Incremental (T1): Cliente '1' mudou do distrito 18 para 54; Cliente '2' igual; Cliente '3' novo
    df_t1 = pd.DataFrame({
        "id_cliente": ["1", "2", "3"],
        "id_distrito": [54, 1, 74],
        "genero": ["F", "M", "F"],
        "idade": [28, 53, 58],
    })
    dw_t1 = loader.apply_scd2_pandas(
        df_target=dw_t0,
        df_incoming=df_t1,
        natural_key="id_cliente",
        tracked_cols=["id_distrito"],
        execution_ts="2026-06-15 19:00:00",
    )

    # Total esperado de linhas = 4 (Cliente 1 antigo + Cliente 1 novo + Cliente 2 + Cliente 3)
    assert len(dw_t1) == 4

    historico_cliente_1 = dw_t1[dw_t1["id_cliente"] == "1"].sort_values("flag_ativo")
    assert len(historico_cliente_1) == 2

    # Linha antiga deve estar inativa (flag_ativo == False) e com distrito 18
    linha_antiga = historico_cliente_1.iloc[0]
    assert bool(linha_antiga["flag_ativo"]) is False
    assert int(linha_antiga["id_distrito"]) == 18
    assert linha_antiga["data_fim_vigencia"] == "2026-06-15 19:00:00"

    # Linha nova deve estar ativa (flag_ativo == True), distrito 54 e data_fim_vigencia nula
    linha_nova = historico_cliente_1.iloc[1]
    assert bool(linha_nova["flag_ativo"]) is True
    assert int(linha_nova["id_distrito"]) == 54
    assert pd.isna(linha_nova["data_fim_vigencia"])