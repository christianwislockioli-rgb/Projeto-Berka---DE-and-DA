# ============================================================================
# DESCRIÇÃO: Pipeline de limpeza, tipagem, datas e tradução de regras de negócio
# ============================================================================
import pandas as pd
import numpy as np
from src.utils.logger import get_logger

logger = get_logger("CleaningPipeline")


class BerkaCleaningPipeline:
    """
    Aplica as regras de limpeza da camada Silver sobre os dados brutos do Banco Berka:
    - Tradução de domínios em checo para português
    - Conversão de datas YYMMDD para o século XX (19YY-MM-DD)
    - Descodificação do birth_number (mês > 50 para mulheres)
    - Remoção de duplicados e tratamento de valores nulos
    """

    FREQ_MAP = {
        "POPLATEK MESICNE": "Emissao Mensal",
        "POPLATEK TYDNE": "Emissao Semanal",
        "POPLATEK PO OBRATU": "Emissao apos Transacao",
    }

    LOAN_STATUS_MAP = {
        "A": "Encerrado - Regular",
        "B": "Encerrado - Inadimplente",
        "C": "Ativo - Regular",
        "D": "Ativo - Inadimplente",
    }

    TRANS_TYPE_MAP = {
        "PRIJEM": "Credito",
        "VYDAJ": "Debito (Saque/Saida)",
        "VYBER": "Saque em Dinheiro",
    }

    K_SYMBOL_MAP = {
        "POJISTNE": "Pagamento de Seguro",
        "SIPO": "Despesas Domesticas",
        "LEASING": "Leasing",
        "UVER": "Pagamento de Emprestimo",
        "SLUZBY": "Taxa de Extrato/Servicos",
        "UROK": "Rendimento de Juros",
        "SANKC. UROK": "Juros Sancionatorios (Saldo Negativo)",
        "DUCHOD": "Pensao por Aposentadoria",
    }

    @staticmethod
    def parse_czech_date(series: pd.Series) -> pd.Series:
        """Converte inteiros/strings no formato YYMMDD para datetime YYYY-MM-DD."""
        cleaned = series.astype(str).str.slice(0, 6).str.zfill(6)
        return pd.to_datetime("19" + cleaned, format="%Y%m%d", errors="coerce")

    def clean_account(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Limpando tabela 'account'...")
        out = df.drop_duplicates(subset=["account_id"]).copy()
        out["id_conta"] = out["account_id"].astype(str)
        out["id_distrito"] = out["district_id"].astype(str)
        out["frequencia"] = out["frequency"].map(self.FREQ_MAP).fillna(out["frequency"])
        out["data"] = self.parse_czech_date(out["date"])
        return out[["id_conta", "id_distrito", "frequencia", "data"]]

    def clean_client(self, df: pd.DataFrame, ref_date: str = "1998-12-31") -> pd.DataFrame:
        logger.info("Limpando tabela 'client' e descodificando birth_number...")
        out = df.drop_duplicates(subset=["client_id"]).copy()
        b_str = out["birth_number"].astype(str).str.zfill(6)

        ano = "19" + b_str.str.slice(0, 2)
        mes_raw = b_str.str.slice(2, 4).astype(int)
        dia = b_str.str.slice(4, 6)

        out["id_cliente"] = out["client_id"].astype(str)
        out["id_distrito"] = out["district_id"].astype(int)
        out["genero"] = np.where(mes_raw > 50, "F", "M")
        mes_limpo = np.where(mes_raw > 50, mes_raw - 50, mes_raw)

        data_str = ano + pd.Series(mes_limpo, index=out.index).astype(str).str.zfill(2) + dia
        out["data_nascimento"] = pd.to_datetime(data_str, format="%Y%m%d", errors="coerce")

        ref_dt = pd.to_datetime(ref_date)
        out["idade"] = ((ref_dt - out["data_nascimento"]).dt.days // 365.25).astype(int)
        return out[["id_cliente", "id_distrito", "genero", "data_nascimento", "idade"]]

    def clean_loan(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Limpando tabela 'loan'...")
        out = df.drop_duplicates(subset=["loan_id"]).copy()
        out["id_emprestimo"] = out["loan_id"].astype(str)
        out["id_conta"] = out["account_id"].astype(str)
        out["data_emprestimo"] = self.parse_czech_date(out["date"])
        out["valor_emprestimo"] = out["amount"].astype(int)
        out["duracao"] = out["duration"].astype(int)
        out["parcelas"] = out["payments"].astype(float)
        out["status_emprestimo"] = out["status"].map(self.LOAN_STATUS_MAP).fillna(out["status"])
        return out[
            [
                "id_emprestimo",
                "id_conta",
                "data_emprestimo",
                "valor_emprestimo",
                "duracao",
                "parcelas",
                "status_emprestimo",
            ]
        ]