-- ============================================================================
-- DESCRIÇÃO: DDL e Merge de Slowly Changing Dimension (SCD Tipo 2) para Clientes
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS portfolio.gold;

-- 1. Criação da Tabela Dimensão de Clientes com Suporte a Histórico (SCD Tipo 2)
CREATE TABLE IF NOT EXISTS portfolio.gold.dim_clientes_scd2 (
    sk_cliente BIGINT GENERATED ALWAYS AS IDENTITY, -- Surrogate Key (Chave Substituta do DW)
    id_cliente STRING NOT NULL,                     -- Natural Key (client_id original)
    id_distrito INT NOT NULL,                       -- Endereço atual/histórico do cliente (district_id)
    genero STRING NOT NULL,                         -- 'M' ou 'F' extraído da regra do birth_number
    ano_nascimento INT NOT NULL,                    -- Ano generalizado em conformidade com a LGPD
    idade INT NOT NULL,                             -- Idade na data-base (1998-12-31)
    hash_scd2 STRING NOT NULL,                      -- Hash SHA-256 dos atributos mutáveis (id_distrito, idade)
    data_inicio_vigencia TIMESTAMP NOT NULL,        -- Data em que o registo passou a valer
    data_fim_vigencia TIMESTAMP,                    -- NULL enquanto o registo for o atual
    flag_ativo BOOLEAN NOT NULL                     -- TRUE para o registo atual, FALSE para histórico fechado
)
USING DELTA;

-- 2. Operação de MERGE INTO (Upsert SCD Tipo 2 no Delta Lake)
-- Fecha a vigência do registo antigo quando o cliente muda de distrito e insere a nova versão
MERGE INTO portfolio.gold.dim_clientes_scd2 AS target
USING (
    -- Subconsulta que prepara os novos dados vindos da camada Silver
    SELECT
        s.id_cliente,
        s.id_distrito,
        s.genero,
        YEAR(s.data_nascimento) AS ano_nascimento,
        s.idade,
        SHA2(CONCAT_WS('||', CAST(s.id_distrito AS STRING), CAST(s.idade AS STRING)), 256) AS hash_scd2,
        s.id_cliente AS merge_key
    FROM portfolio.silver.client s

    UNION ALL

    -- Linhas duplicadas com merge_key = NULL para forçar o INSERT da nova versão dos clientes alterados
    SELECT
        s.id_cliente,
        s.id_distrito,
        s.genero,
        YEAR(s.data_nascimento) AS ano_nascimento,
        s.idade,
        SHA2(CONCAT_WS('||', CAST(s.id_distrito AS STRING), CAST(s.idade AS STRING)), 256) AS hash_scd2,
        NULL AS merge_key
    FROM portfolio.silver.client s
    INNER JOIN portfolio.gold.dim_clientes_scd2 t
        ON s.id_cliente = t.id_cliente AND t.flag_ativo = TRUE
    WHERE t.hash_scd2 <> SHA2(CONCAT_WS('||', CAST(s.id_distrito AS STRING), CAST(s.idade AS STRING)), 256)
) AS staged_updates
ON target.id_cliente = staged_updates.merge_key AND target.flag_ativo = TRUE

-- Se o cliente já existe ativo e mudou de endereço/atributo, fecha o registo antigo
WHEN MATCHED AND target.hash_scd2 <> staged_updates.hash_scd2 THEN
    UPDATE SET
        target.data_fim_vigencia = current_timestamp(),
        target.flag_ativo = FALSE

-- Se é um cliente novo OU a nova versão de um cliente que mudou, insere como ativo
WHEN NOT MATCHED THEN
    INSERT (
        id_cliente, id_distrito, genero, ano_nascimento, idade,
        hash_scd2, data_inicio_vigencia, data_fim_vigencia, flag_ativo
    )
    VALUES (
        staged_updates.id_cliente,
        staged_updates.id_distrito,
        staged_updates.genero,
        staged_updates.ano_nascimento,
        staged_updates.idade,
        staged_updates.hash_scd2,
        current_timestamp(),
        NULL,
        TRUE
    );