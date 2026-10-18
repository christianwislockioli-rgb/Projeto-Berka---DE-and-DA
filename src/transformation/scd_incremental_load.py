# ============================================================================
# DESCRIÇÃO: Motor de Carga Incremental Slowly Changing Dimension (SCD Tipo 2)
# ============================================================================
import hashlib
from datetime import datetime, timezone
from typing import List
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger("SCD2IncrementalLoader")


class SCD2Loader:
    """
    Executa a lógica de Slowly Changing Dimension Tipo 2 (SCD2) para manter
    o histórico temporal de clientes que mudaram de distrito ou faixa etária.
    """

    @staticmethod
    def _compute_row_hash(df: pd.DataFrame, tracked_cols: List[str]) -> pd.Series:
        """Gera um hash SHA-256 concatenando os atributos monitorados para detetar mudanças."""
        combined = df[tracked_cols].astype(str).agg("||".join, axis=1)
        return combined.apply(lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest())

    def apply_scd2_pandas(
        self,
        df_target: pd.DataFrame,
        df_incoming: pd.DataFrame,
        natural_key: str = "id_cliente",
        tracked_cols: List[str] | None = None,
        execution_ts: str | None = None,
    ) -> pd.DataFrame:
        """
        Aplica Upsert/Merge SCD Tipo 2 sobre um DataFrame existente:
        1. Registos inalterados permanecem intactos.
        2. Clientes que mudaram de atributo (ex: id_distrito) têm a linha antiga fechada
           (flag_ativo = False, data_fim_vigencia = execution_ts) e uma nova linha ativa inserida.
        3. Novos clientes são inseridos diretamente com flag_ativo = True.
        """
        tracked_cols = tracked_cols or ["id_distrito"]
        now_ts = execution_ts or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        incoming = df_incoming.copy()
        incoming["hash_scd2"] = self._compute_row_hash(incoming, tracked_cols)

        # Carga Inicial caso a tabela de destino esteja vazia
        if df_target.empty:
            logger.info("Tabela destino vazia. Executando carga inicial SCD Tipo 2...")
            incoming["data_inicio_vigencia"] = now_ts
            incoming["data_fim_vigencia"] = None
            incoming["flag_ativo"] = True
            return incoming.reset_index(drop=True)

        target = df_target.copy()
        if "hash_scd2" not in target.columns:
            target["hash_scd2"] = self._compute_row_hash(target, tracked_cols)

        active_target = target[target["flag_ativo"] == True].copy()
        inactive_target = target[target["flag_ativo"] == False].copy()

        # Cruzamento entre registos ativos atuais e novos dados recebidos
        merged = pd.merge(
            incoming,
            active_target[[natural_key, "hash_scd2"]],
            on=natural_key,
            how="left",
            suffixes=("_new", "_old"),
        )

        # 1. Novos clientes (não existiam na dimensão)
        new_keys = merged[merged["hash_scd2_old"].isna()][natural_key].tolist()
        df_new_inserts = incoming[incoming[natural_key].isin(new_keys)].copy()
        df_new_inserts["data_inicio_vigencia"] = now_ts
        df_new_inserts["data_fim_vigencia"] = None
        df_new_inserts["flag_ativo"] = True

        # 2. Clientes que sofreram alteração nos atributos monitorados (ex: mudaram de distrito)
        changed_mask = merged["hash_scd2_old"].notna() & (merged["hash_scd2_new"] != merged["hash_scd2_old"])
        changed_keys = merged[changed_mask][natural_key].tolist()

        # Fecha vigência dos registos antigos que mudaram
        active_target.loc[active_target[natural_key].isin(changed_keys), "data_fim_vigencia"] = now_ts
        active_target.loc[active_target[natural_key].isin(changed_keys), "flag_ativo"] = False

        # Cria as novas linhas ativas para os clientes que mudaram
        df_changed_inserts = incoming[incoming[natural_key].isin(changed_keys)].copy()
        df_changed_inserts["data_inicio_vigencia"] = now_ts
        df_changed_inserts["data_fim_vigencia"] = None
        df_changed_inserts["flag_ativo"] = True

        logger.info(
            f"SCD2 concluído -> Novos clientes: {len(new_keys)} | "
            f"Históricos atualizados (SCD2): {len(changed_keys)}"
        )

        result = pd.concat(
            [inactive_target, active_target, df_changed_inserts, df_new_inserts],
            ignore_index=True,
        )
        return result