-- ============================================================================
-- DESCRIÇÃO: Modelagem Dimensional Star Schema (Tabelas Fato e Dimensões Gold)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS portfolio.gold;

-- 1. DIMENSÃO CONTA
CREATE TABLE IF NOT EXISTS portfolio.gold.dim_conta (
    id_conta STRING NOT NULL,
    id_distrito STRING NOT NULL,
    frequencia STRING,
    data_criacao DATE,
    CONSTRAINT pk_dim_conta PRIMARY KEY (id_conta)
) USING DELTA;

-- 2. DIMENSÃO DISTRITO (Demografia Regional)
CREATE TABLE IF NOT EXISTS portfolio.gold.dim_distrito (
    id_distrito INT NOT NULL,
    nome_distrito STRING,
    regiao STRING,
    tipo_zona STRING,
    habitantes INT,
    proporcao_urbana DOUBLE,
    salario_medio DOUBLE,
    taxa_desemprego_95 DOUBLE,
    taxa_desemprego_96 DOUBLE,
    empreendedores_por_1000 INT,
    crimes_95 INT,
    crimes_96 INT,
    CONSTRAINT pk_dim_distrito PRIMARY KEY (id_distrito)
) USING DELTA;

-- 3. DIMENSÃO DISPOSIÇÃO (Vínculo Titular / Dependente)
CREATE TABLE IF NOT EXISTS portfolio.gold.dim_Disposicao (
    id_disp STRING NOT NULL,
    id_cliente STRING NOT NULL,
    id_conta STRING NOT NULL,
    tipo_disposicao STRING,
    CONSTRAINT pk_dim_disposicao PRIMARY KEY (id_disp)
) USING DELTA;

-- 4. DIMENSÃO CARTÃO DE CRÉDITO
CREATE TABLE IF NOT EXISTS portfolio.gold.dim_cartao (
    id_cartao STRING NOT NULL,
    id_disp STRING NOT NULL,
    tipo_cartao STRING,
    data_emissao DATE,
    CONSTRAINT pk_dim_cartao PRIMARY KEY (id_cartao)
) USING DELTA;

-- 5. TABELA FATO: TRANSAÇÕES BANCÁRIAS (1.056.320 registos)
CREATE TABLE IF NOT EXISTS portfolio.gold.fato_transacoes (
    id_transacao INT NOT NULL,
    id_conta STRING NOT NULL,
    data_transacao DATE NOT NULL,
    tipo_transacao STRING,
    operacao STRING,
    valor DOUBLE NOT NULL,
    saldo DOUBLE NOT NULL,
    simbolo_k STRING,
    banco_parceiro STRING,
    conta_parceiro_hash STRING,
    CONSTRAINT pk_fato_transacoes PRIMARY KEY (id_transacao)
) USING DELTA;

-- 6. TABELA FATO: EMPRÉSTIMOS (682 contratos)
CREATE TABLE IF NOT EXISTS portfolio.gold.fato_emprestimos (
    id_emprestimo STRING NOT NULL,
    id_conta STRING NOT NULL,
    data_emprestimo DATE NOT NULL,
    valor_emprestimo INT NOT NULL,
    duracao INT NOT NULL,
    parcelas DOUBLE NOT NULL,
    status_codigo STRING,
    status_emprestimo STRING NOT NULL,
    CONSTRAINT pk_fato_emprestimos PRIMARY KEY (id_emprestimo)
) USING DELTA;

-- 7. TABELA FATO: ORDENS PERMANENTES (6.471 débitos automáticos)
CREATE TABLE IF NOT EXISTS portfolio.gold.fato_ordem (
    id_ordem STRING NOT NULL,
    id_conta STRING NOT NULL,
    banco_destino STRING,
    conta_destino_hash STRING,
    valor_ordem DOUBLE NOT NULL,
    caracterizacao_pagamento STRING,
    CONSTRAINT pk_fato_ordem PRIMARY KEY (id_ordem)
) USING DELTA;