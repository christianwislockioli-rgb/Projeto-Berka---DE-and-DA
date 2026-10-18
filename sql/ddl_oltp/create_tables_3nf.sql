-- ============================================================================
-- ARQUIVO: sql/ddl_oltp/create_tables_3nf.sql
-- DESCRIÇÃO: Modelagem Transacional Normalizada (3FN) - Banco Berka (OLTP)
-- ============================================================================

-- 1. TABELA DE DISTRITOS / DEMOGRAFIA (Entidade Forte - Evita dependência transitiva na 3FN)
CREATE TABLE IF NOT EXISTS district (
    district_id INT PRIMARY KEY,
    district_name VARCHAR(100) NOT NULL,          -- A2: Nome do distrito
    region VARCHAR(100) NOT NULL,                 -- A3: Região da República Checa
    inhabitants INT NOT NULL,                     -- A4: Número de habitantes
    municipalities_lt_499 INT,                    -- A5: Municípios < 499 hab.
    municipalities_500_1999 INT,                  -- A6: Municípios 500-1999 hab.
    municipalities_2000_9999 INT,                 -- A7: Municípios 2000-9999 hab.
    municipalities_gt_10000 INT,                  -- A8: Municípios > 10000 hab.
    cities INT,                                   -- A9: Número de cidades
    urban_ratio DECIMAL(5,2),                     -- A10: Proporção urbana (%)
    average_salary DECIMAL(10,2),                 -- A11: Salário médio
    unemployment_rate_95 DECIMAL(5,2),            -- A12: Taxa de desemprego 1995
    unemployment_rate_96 DECIMAL(5,2),            -- A13: Taxa de desemprego 1996
    entrepreneurs_per_1000 INT,                   -- A14: Empreendedores por 1000 hab.
    committed_crimes_95 INT,                      -- A15: Crimes cometidos em 1995
    committed_crimes_96 INT                       -- A16: Crimes cometidos em 1996
);

-- 2. TABELA DE CONTAS BANCÁRIAS (1FN/2FN/3FN - Referencia a agência via FK district_id)
CREATE TABLE IF NOT EXISTS account (
    account_id INT PRIMARY KEY,
    district_id INT NOT NULL,
    frequency VARCHAR(30) NOT NULL CHECK (
        frequency IN ('POPLATEK MESICNE', 'POPLATEK TYDNE', 'POPLATEK PO OBRATU')
    ),
    creation_date DATE NOT NULL,
    CONSTRAINT fk_account_district FOREIGN KEY (district_id) 
        REFERENCES district (district_id) ON UPDATE CASCADE
);

-- 3. TABELA DE CLIENTES (Dados exclusivos do indivíduo)
CREATE TABLE IF NOT EXISTS client (
    client_id INT PRIMARY KEY,
    birth_number VARCHAR(10) NOT NULL,            -- Formato original YYMMDD (H) ou YYMM+50DD (M)
    district_id INT NOT NULL,
    CONSTRAINT fk_client_district FOREIGN KEY (district_id) 
        REFERENCES district (district_id) ON UPDATE CASCADE
);

-- 4. TABELA DE DISPOSIÇÃO / VÍNCULO (Resolve relação N:N entre Cliente e Conta na 2FN)
CREATE TABLE IF NOT EXISTS disp (
    disp_id INT PRIMARY KEY,
    client_id INT NOT NULL,
    account_id INT NOT NULL,
    type VARCHAR(15) NOT NULL CHECK (type IN ('OWNER', 'DISPONENT')),
    CONSTRAINT uq_client_account UNIQUE (client_id, account_id),
    CONSTRAINT fk_disp_client FOREIGN KEY (client_id) 
        REFERENCES client (client_id) ON DELETE CASCADE,
    CONSTRAINT fk_disp_account FOREIGN KEY (account_id) 
        REFERENCES account (account_id) ON DELETE CASCADE
);

-- 5. TABELA DE CARTÕES DE CRÉDITO (Associada ao vínculo de disposição disp_id)
CREATE TABLE IF NOT EXISTS card (
    card_id INT PRIMARY KEY,
    disp_id INT NOT NULL,
    type VARCHAR(15) NOT NULL CHECK (type IN ('junior', 'classic', 'gold')),
    issued_date DATE NOT NULL,
    CONSTRAINT fk_card_disp FOREIGN KEY (disp_id) 
        REFERENCES disp (disp_id) ON DELETE CASCADE
);

-- 6. TABELA DE ORDENS PERMANENTES (Débitos automáticos parametrizados por conta)
CREATE TABLE IF NOT EXISTS permanent_order (
    order_id INT PRIMARY KEY,
    account_id INT NOT NULL,
    bank_to CHAR(2) NOT NULL,
    account_to VARCHAR(20) NOT NULL,
    amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    k_symbol VARCHAR(20) CHECK (k_symbol IN ('POJISTNE', 'SIPO', 'LEASING', 'UVER', ' ')),
    CONSTRAINT fk_order_account FOREIGN KEY (account_id) 
        REFERENCES account (account_id) ON DELETE CASCADE
);

-- 7. TABELA DE EMPRÉSTIMOS (No máximo 1 empréstimo por conta segundo regra de negócio)
CREATE TABLE IF NOT EXISTS loan (
    loan_id INT PRIMARY KEY,
    account_id INT NOT NULL UNIQUE,               -- Garante a regra: no máximo 1 empréstimo por conta
    granted_date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    duration INT NOT NULL CHECK (duration IN (12, 24, 36, 48, 60)),
    payments DECIMAL(12,2) NOT NULL CHECK (payments > 0),
    status CHAR(1) NOT NULL CHECK (status IN ('A', 'B', 'C', 'D')),
    CONSTRAINT fk_loan_account FOREIGN KEY (account_id) 
        REFERENCES account (account_id) ON DELETE RESTRICT
);

-- 8. TABELA DE TRANSAÇÕES FINANCEIRAS (Registo atómico de movimentações)
CREATE TABLE IF NOT EXISTS trans (
    trans_id INT PRIMARY KEY,
    account_id INT NOT NULL,
    trans_date DATE NOT NULL,
    type VARCHAR(15) NOT NULL CHECK (type IN ('PRIJEM', 'VYDAJ', 'VYBER')),
    operation VARCHAR(30) CHECK (
        operation IN ('VYBER KARTOU', 'VKLAD', 'PREVOD Z UCTU', 'VYBER', 'PREVOD NA UCET')
    ),
    amount DECIMAL(12,2) NOT NULL CHECK (amount >= 0),
    balance DECIMAL(14,2) NOT NULL,
    k_symbol VARCHAR(20),
    bank CHAR(2),
    partner_account VARCHAR(20),
    CONSTRAINT fk_trans_account FOREIGN KEY (account_id) 
        REFERENCES account (account_id) ON DELETE RESTRICT
);

-- Índices de performance para chaves estrangeiras de alto volume
CREATE INDEX IF NOT EXISTS idx_trans_account_date ON trans (account_id, trans_date);
CREATE INDEX IF NOT EXISTS idx_disp_account ON disp (account_id);
CREATE INDEX IF NOT EXISTS idx_client_district ON client (district_id);