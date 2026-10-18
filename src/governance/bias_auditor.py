# ============================================================================
# DESCRIÇÃO: Auditoria estatística de viés demográfico e discriminação em crédito
# ============================================================================
from typing import Dict, Any
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from src.utils.logger import get_logger

logger = get_logger("BiasAuditor")


class CreditBiasAuditor:
    """
    Audita viés algorítmico e estatístico em concessão de empréstimos e emissão de cartões
    utilizando Disparate Impact Ratio (Regra dos 80%) e Teste Qui-Quadrado de Independência.
    """

    DISPARATE_IMPACT_MIN = 0.80
    DISPARATE_IMPACT_MAX = 1.25
    ALPHA = 0.05

    def audit_representation(self, df: pd.DataFrame, demographic_col: str = "genero") -> Dict[str, float]:
        """
        Verifica se há sub-representação grave de algum grupo demográfico no dataset.
        """
        if demographic_col not in df.columns:
            raise ValueError(f"Coluna demográfica '{demographic_col}' não encontrada no DataFrame.")

        proportions = df[demographic_col].value_counts(normalize=True).round(4).to_dict()
        logger.info(f"Distribuição demográfica para '{demographic_col}': {proportions}")
        return proportions

    def audit_disparate_impact(
        self,
        df: pd.DataFrame,
        protected_col: str,
        privileged_group: str,
        unprivileged_group: str,
        outcome_col: str,
        favorable_value: Any,
    ) -> Dict[str, Any]:
        """
        Calcula o Disparate Impact (DI) e o p-valor do teste Qui-Quadrado entre dois grupos.
        Exemplo no Banco Berka:
          - protected_col='genero', privileged_group='M', unprivileged_group='F'
          - outcome_col='status_emprestimo', favorable_value='Ativo - Regular' (ou possui_cartao=1)
        """
        subset = df[df[protected_col].isin([privileged_group, unprivileged_group])].copy()
        subset["is_favorable"] = (subset[outcome_col] == favorable_value).astype(int)

        rates = subset.groupby(protected_col)["is_favorable"].mean()
        rate_priv = float(rates.get(privileged_group, 0.0))
        rate_unpriv = float(rates.get(unprivileged_group, 0.0))

        # Cálculo do Disparate Impact Ratio: P(Y=1 | D=unpriv) / P(Y=1 | D=priv)
        if rate_priv == 0:
            di_ratio = np.nan
        else:
            di_ratio = round(rate_unpriv / rate_priv, 4)

        # Teste Qui-Quadrado de Independência (H0: Desfecho independe do grupo demográfico)
        contingency_table = pd.crosstab(subset[protected_col], subset["is_favorable"])
        if contingency_table.shape == (2, 2):
            chi2_stat, p_value, _, _ = chi2_contingency(contingency_table)
        else:
            chi2_stat, p_value = 0.0, 1.0

        is_fair_80_rule = bool(
            not np.isnan(di_ratio) and (self.DISPARATE_IMPACT_MIN <= di_ratio <= self.DISPARATE_IMPACT_MAX)
        )
        statistically_significant_bias = bool(p_value < self.ALPHA and not is_fair_80_rule)

        report = {
            "protected_attribute": protected_col,
            "privileged_group": privileged_group,
            "unprivileged_group": unprivileged_group,
            "privileged_favorable_rate": round(rate_priv, 4),
            "unprivileged_favorable_rate": round(rate_unpriv, 4),
            "disparate_impact_ratio": di_ratio,
            "passes_80_percent_rule": is_fair_80_rule,
            "chi2_statistic": round(float(chi2_stat), 4),
            "p_value": round(float(p_value), 4),
            "has_discriminatory_bias": statistically_significant_bias,
        }

        logger.info(f"Resultado da Auditoria de Viés ({protected_col}): {report}")
        return report