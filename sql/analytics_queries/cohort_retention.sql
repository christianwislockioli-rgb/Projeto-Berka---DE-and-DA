-- ============================================================================
-- ARQUIVO: sql/analytics_queries/cohort_retention.sql
-- DESCRIÇÃO: Análise de Retenção por Safra (Cohort) e Trajetória Mensal (LAG/LEAD)
-- COMPATIBILIDADE: Databricks SQL (Unity Catalog) / Amazon Athena / Spark SQL
-- ============================================================================

-- ============================================================================
-- CONSULTA 1: MATRIZ DE RETENÇÃO DE SAFRAS (COHORT RETENTION ANALYSIS)
-- Objetivo: Medir a retenção transacional das contas desde o mês de entrada
-- ============================================================================
WITH primeira_transacao_conta AS (
    -- Identifica o mês de aquisição (Safra / Cohort) de cada conta bancária
    SELECT
        id_conta,
        DATE_TRUNC('MONTH', MIN(data_transacao)) AS mes_safra
    FROM portfolio.gold.fato_transacoes
    GROUP BY id_conta
),

atividade_mensal AS (
    -- Mapeia todos os meses em que cada conta realizou movimentações financeiras
    SELECT DISTINCT
        t.id_conta,
        p.mes_safra,
        DATE_TRUNC('MONTH', t.data_transacao) AS mes_atividade,
        CAST(MONTHS_BETWEEN(DATE_TRUNC('MONTH', t.data_transacao), p.mes_safra) AS INT) AS indice_mes
    FROM portfolio.gold.fato_transacoes t
    INNER JOIN primeira_transacao_conta p
        ON t.id_conta = p.id_conta
),

contagem_safra AS (
    -- Conta o volume de clientes ativos em cada safra e índice de mês (M0, M1, M2...)
    SELECT
        mes_safra,
        indice_mes,
        COUNT(DISTINCT id_conta) AS contas_ativas
    FROM atividade_mensal
    WHERE indice_mes BETWEEN 0 AND 24
    GROUP BY mes_safra, indice_mes
),

tamanho_inicial_safra AS (
    -- Usa Window Function FIRST_VALUE() para fixar a base inicial (M0) de cada Cohort
    SELECT
        mes_safra,
        indice_mes,
        contas_ativas,
        FIRST_VALUE(contas_ativas) OVER (
            PARTITION BY mes_safra
            ORDER BY indice_mes ASC
        ) AS total_clientes_safra_m0
    FROM contagem_safra
)

SELECT
    DATE_FORMAT(mes_safra, 'yyyy-MM') AS safra_aquisicao,
    indice_mes AS meses_apos_abertura,
    total_clientes_safra_m0,
    contas_ativas,
    ROUND((contas_ativas * 100.0) / NULLIF(total_clientes_safra_m0, 0), 2) AS taxa_retencao_pct
FROM tamanho_inicial_safra
ORDER BY safra_aquisicao ASC, meses_apos_abertura ASC;


-- ============================================================================
-- CONSULTA 2: CRESCIMENTO MONTH-OVER-MONTH (MoM) E ALERTA DE LIQUIDEZ (LAG / LEAD)
-- Objetivo: Monitorizar variações mensais de saldo e prever risco de saldo negativo
-- ============================================================================
WITH resumo_mensal_conta AS (
    SELECT
        id_conta,
        DATE_TRUNC('MONTH', data_transacao) AS mes_referencia,
        SUM(valor) AS volume_movimentado_mes,
        AVG(saldo) AS saldo_medio_mes,
        COUNT(id_transacao) AS qtd_transacoes_mes
    FROM portfolio.gold.fato_transacoes
    GROUP BY id_conta, DATE_TRUNC('MONTH', data_transacao)
),

analise_temporal_window AS (
    SELECT
        id_conta,
        mes_referencia,
        ROUND(volume_movimentado_mes, 2) AS volume_movimentado_mes,
        ROUND(saldo_medio_mes, 2) AS saldo_medio_atual,
        -- LAG(): Busca o saldo médio do mês imediatamente anterior
        ROUND(LAG(saldo_medio_mes, 1) OVER (
            PARTITION BY id_conta
            ORDER BY mes_referencia ASC
        ), 2) AS saldo_medio_mes_anterior,
        -- LEAD(): Observa o saldo médio do mês seguinte (para backtesting de modelos de risco)
        ROUND(LEAD(saldo_medio_mes, 1) OVER (
            PARTITION BY id_conta
            ORDER BY mes_referencia ASC
        ), 2) AS saldo_medio_mes_seguinte,
        -- SUM() OVER(): Soma acumulada (Running Total) do volume transacionado pela conta
        ROUND(SUM(volume_movimentado_mes) OVER (
            PARTITION BY id_conta
            ORDER BY mes_referencia ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 2) AS volume_acumulado_historico
    FROM resumo_mensal_conta
)

SELECT
    id_conta,
    DATE_FORMAT(mes_referencia, 'yyyy-MM') AS ano_mes,
    volume_movimentado_mes,
    saldo_medio_mes_anterior,
    saldo_medio_atual,
    saldo_medio_mes_seguinte,
    ROUND(
        ((saldo_medio_atual - saldo_medio_mes_anterior) / NULLIF(ABS(saldo_medio_mes_anterior), 0)) * 100,
        2
    ) AS variacao_mom_pct,
    volume_acumulado_historico
FROM analise_temporal_window
WHERE saldo_medio_mes_anterior IS NOT NULL
ORDER BY id_conta ASC, ano_mes ASC;