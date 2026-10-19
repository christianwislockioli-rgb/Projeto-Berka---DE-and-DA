-- ============================================================================
-- ARQUIVO: sql/analytics_queries/ranking_faturamento.sql
-- DESCRIÇÃO: Rankings Regionais (RANK, DENSE_RANK, ROW_NUMBER) e Motor de
--            Elegibilidade de Cartões de Crédito (Regras PKDD'99 Banco Berka)
-- ============================================================================

-- ============================================================================
-- CONSULTA 1: RANKING DE DISTRITOS E REGIÕES POR VOLUME DE CRÉDITO E INADIMPLÊNCIA
-- Demonstração de: CTEs, JOINs, SUM() OVER(), ROW_NUMBER(), RANK() e DENSE_RANK()
-- ============================================================================
WITH metricas_distrito AS (
    SELECT
        d.id_distrito,
        d.nome_distrito,
        d.regiao,
        d.tipo_zona,
        d.salario_medio,
        COUNT(DISTINCT c.id_conta) AS total_contas,
        COUNT(DISTINCT e.id_emprestimo) AS qtd_emprestimos,
        COALESCE(SUM(e.valor_emprestimo), 0) AS volume_total_emprestado,
        COALESCE(SUM(
            CASE WHEN e.status_emprestimo LIKE '%Inadimplente%' THEN e.valor_emprestimo ELSE 0 END
        ), 0) AS volume_em_inadimplencia
    FROM portfolio.gold.dim_distrito d
    LEFT JOIN portfolio.gold.dim_conta c
        ON CAST(d.id_distrito AS STRING) = CAST(c.id_distrito AS STRING)
    LEFT JOIN portfolio.gold.fato_emprestimos e
        ON c.id_conta = e.id_conta
    GROUP BY
        d.id_distrito, d.nome_distrito, d.regiao, d.tipo_zona, d.salario_medio
),

rankings_calculados AS (
    SELECT
        *,
        -- Taxa de inadimplência (Default Rate) do distrito
        ROUND((volume_em_inadimplencia * 100.0) / NULLIF(volume_total_emprestado, 0), 2) AS taxa_inadimplencia_pct,
        -- Share (%) do distrito sobre o volume de crédito da sua Região
        ROUND(
            (volume_total_emprestado * 100.0) / NULLIF(SUM(volume_total_emprestado) OVER (PARTITION BY regiao), 0),
            2
        ) AS share_regional_pct,
        -- Window Functions de Ranking dentro de cada Região e no Geral
        ROW_NUMBER() OVER (PARTITION BY regiao ORDER BY volume_total_emprestado DESC) AS row_num_regiao,
        RANK() OVER (ORDER BY volume_total_emprestado DESC) AS rank_geral_faturamento,
        DENSE_RANK() OVER (PARTITION BY tipo_zona ORDER BY volume_total_emprestado DESC) AS dense_rank_por_zona
    FROM metricas_distrito
)

SELECT
    rank_geral_faturamento,
    regiao,
    row_num_regiao AS posicao_na_regiao,
    nome_distrito,
    tipo_zona,
    dense_rank_por_zona,
    salario_medio,
    total_contas,
    qtd_emprestimos,
    volume_total_emprestado,
    volume_em_inadimplencia,
    COALESCE(taxa_inadimplencia_pct, 0.0) AS taxa_inadimplencia_pct,
    COALESCE(share_regional_pct, 0.0) AS share_regional_pct
FROM rankings_calculados
ORDER BY rank_geral_faturamento ASC;


-- ============================================================================
-- CONSULTA 2: VISÃO 360º DO CLIENTE (TITULAR + DEPENDENTE) & MOTOR DE OFERTA DE CARTÃO
-- Refina o cruzamento iniciado no notebook Analise_Descritiva_Dados.ipynb e aplica
-- as regras matemáticas de recomendação do estudo PKDD'99 (Banco Berka.pdf)
-- ============================================================================
WITH saldo_por_conta AS (
    SELECT
        id_conta,
        ROUND(AVG(saldo), 2) AS saldo_medio_conta,
        COUNT(id_transacao) AS total_transacoes
    FROM portfolio.gold.fato_transacoes
    GROUP BY id_conta
),

vinculo_clientes AS (
    SELECT
        dp.id_conta,
        dp.id_disp,
        dp.id_cliente,
        dp.tipo_disposicao,
        cl.genero,
        cl.idade,
        cl.id_distrito,
        ca.id_cartao,
        ca.tipo_cartao
    FROM portfolio.gold.dim_Disposicao dp
    INNER JOIN portfolio.gold.dim_cliente cl
        ON dp.id_cliente = cl.id_cliente
    LEFT JOIN portfolio.gold.dim_cartao ca
        ON dp.id_disp = ca.id_disp
),

titulares AS (
    SELECT * FROM vinculo_clientes WHERE UPPER(tipo_disposicao) IN ('TITULAR', 'OWNER')
),

dependentes AS (
    SELECT * FROM vinculo_clientes WHERE UPPER(tipo_disposicao) NOT IN ('TITULAR', 'OWNER')
)

SELECT
    t.id_conta,
    t.id_cliente AS id_cliente_titular,
    t.genero AS genero_titular,
    t.idade AS idade_titular,
    d.id_cliente AS id_cliente_dependente,
    d.genero AS genero_dependente,
    d.idade AS idade_dependente,
    dist.nome_distrito,
    dist.regiao,
    dist.tipo_zona,
    s.saldo_medio_conta,
    COALESCE(t.tipo_cartao, 'Sem Cartao') AS cartao_atual,
    COALESCE(emp.status_emprestimo, 'Sem Emprestimo') AS status_emprestimo,
    -- Motor de Recomendação de Cartão de Crédito baseado nas descobertas do Banco Berka
    CASE
        WHEN t.id_cartao IS NOT NULL THEN 'Cliente Ja Possui Cartao'
        WHEN emp.status_emprestimo LIKE '%Inadimplente%' THEN 'Bloqueado - Risco de Inadimplencia'
        WHEN s.saldo_medio_conta <= 37097.18 THEN 'Inelegivel (Saldo <= 37.097,18 CZK)'
        WHEN t.idade < 24 AND s.saldo_medio_conta > 37097.18 AND s.saldo_medio_conta < 50000.00
            THEN 'Elegivel - Ofertar Cartao JUNIOR'
        WHEN UPPER(dist.nome_distrito) LIKE '%PRAHA%' AND t.idade BETWEEN 35 AND 55 AND s.saldo_medio_conta > 66899.77
            THEN 'Elegivel Prioritario (Praga) - Ofertar Cartao GOLD/CLASSIC'
        WHEN UPPER(dist.nome_distrito) LIKE '%PROSTEJOV%' AND s.saldo_medio_conta > 46123.76
            THEN 'Elegivel Regional (Prostejov) - Ofertar Cartao CLASSIC'
        WHEN t.genero = 'F' AND d.id_cliente IS NULL AND t.idade BETWEEN 35 AND 55 AND s.saldo_medio_conta > 50000.00
            THEN 'Elegivel Perfil Feminino Single - Ofertar Cartao GOLD/CLASSIC'
        ELSE 'Elegivel Padrao - Avaliar Comportamento Transacional'
    END AS recomendacao_oferta_cartao
FROM titulares t
LEFT JOIN dependentes d
    ON t.id_conta = d.id_conta
LEFT JOIN portfolio.gold.dim_distrito dist
    ON CAST(t.id_distrito AS INT) = CAST(dist.id_distrito AS INT)
LEFT JOIN saldo_por_conta s
    ON t.id_conta = s.id_conta
LEFT JOIN portfolio.gold.fato_emprestimos emp
    ON t.id_conta = emp.id_conta
-- Subconsulta: Filtra contas cujo saldo médio supera o 1º quartil global (22.400 CZK)
WHERE s.saldo_medio_conta >= (
    SELECT PERCENTILE_APPROX(saldo, 0.25)
    FROM portfolio.gold.fato_transacoes
)
ORDER BY s.saldo_medio_conta DESC;