# ============================================================================
# ARQUIVO: tests/test_lgpd_masking.py
# DESCRIÇÃO: Testes unitários automatizados (Pytest) de LGPD e Viés Estatístico
# ============================================================================
import re
import pandas as pd
from src.governance.lgpd_anonymizer import LGPDAnonymizer
from src.governance.bias_auditor import CreditBiasAuditor


def test_birth_number_and_pii_are_hashed_sha256():
    """
    Garante que o birth_number (Rodné číslo tcheco) e contas de terceiros
    sejam convertidos em hashes SHA-256 de 64 caracteres e nunca passem abertos.
    """
    raw_df = pd.DataFrame({
        "id_cliente": ["1", "2"],
        "birth_number": ["706213", "450204"],  # Formato original YYMM+50DD (F) e YYMMDD (M)
        "genero": ["F", "M"],
        "data_nascimento": ["1970-12-13", "1945-02-04"],
        "idade": [28, 53],
        "account_to": ["12345678", "87654321"]
    })

    anonymizer = LGPDAnonymizer(salt="test_salt_fixo")
    gold_df = anonymizer.anonymize_pandas_client(raw_df, drop_raw_pii=True)

    # 1. Nenhuma data de nascimento exata deve existir na tabela final
    assert "data_nascimento" not in gold_df.columns
    assert "ano_nascimento" in gold_df.columns
    assert list(gold_df["ano_nascimento"]) == [1970, 1945]

    # 2. Os valores originais de birth_number não podem existir em texto plano
    assert "706213" not in gold_df["birth_number"].values
    assert "450204" not in gold_df["birth_number"].values

    # 3. Todos os hashes gerados devem ser strings hexadecimais válidas de 64 caracteres (SHA-256)
    sha256_regex = re.compile(r"^[a-f0-9]{64}$")
    for hashed_val in gold_df["birth_number"]:
        assert bool(sha256_regex.match(hashed_val))


def test_bias_auditor_detects_gender_parity_and_discrimination():
    """
    Verifica se o auditor aprova distribuições equilibradas (como a emissão de cartões
    no Banco Berka) e sinaliza viés quando a Regra dos 80% é violada.
    """
    auditor = CreditBiasAuditor()

    # Cenário 1: Equilibrado (Sem viés entre Homens e Mulheres)
    df_fair = pd.DataFrame({
        "genero": ["M"] * 50 + ["F"] * 50,
        "possui_cartao": [1] * 25 + [0] * 25 + [1] * 24 + [0] * 26
    })
    res_fair = auditor.audit_disparate_impact(
        df_fair,
        protected_col="genero",
        privileged_group="M",
        unprivileged_group="F",
        outcome_col="possui_cartao",
        favorable_value=1
    )
    assert res_fair["passes_80_percent_rule"] is True
    assert res_fair["has_discriminatory_bias"] is False

    # Cenário 2: Enviesado (Mulheres com taxa de aprovação drasticamente menor)
    df_biased = pd.DataFrame({
        "genero": ["M"] * 100 + ["F"] * 100,
        "possui_cartao": [1] * 80 + [0] * 20 + [1] * 20 + [0] * 80
    })
    res_biased = auditor.audit_disparate_impact(
        df_biased,
        protected_col="genero",
        privileged_group="M",
        unprivileged_group="F",
        outcome_col="possui_cartao",
        favorable_value=1
    )
    assert res_biased["disparate_impact_ratio"] == 0.25
    assert res_biased["passes_80_percent_rule"] is False
    assert res_biased["has_discriminatory_bias"] is True