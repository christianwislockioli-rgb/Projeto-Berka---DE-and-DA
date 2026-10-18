# Dicionário de Dados — Arquitetura Medalhão (Banco Berka)

Este documento mapeia a linhagem completa dos dados desde os arquivos brutos originais em tcheco (**Camada Bronze**), passando pela padronização, tradução e enriquecimento (**Camada Silver**), até a modelagem dimensional Star Schema (**Camada Gold**) no catálogo `portfolio` do Databricks Unity Catalog.

---

## 1. Visão Geral das Entidades e Volumetria

| Tabela Original (`.asc`) | Tabela Bronze (`portfolio.bronze`) | Tabela Silver (`portfolio.silver`) | Tabela(s) Gold (`portfolio.gold`) | Volumetria Aproximada | Descrição da Entidade |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `account.asc` | `account` | `account` | `dim_conta` | $4.500$ | Contas bancárias e frequência de emissão de extratos. |
| `client.asc` | `client` | `client` | `dim_cliente` | $5.369$ | Dados cadastrais e demográficos dos clientes. |
| `disp.asc` | `disp` | `disp` | `dim_Disposicao` | $5.369$ | Vínculo de permissão entre clientes e contas (`OWNER` / `DISPONENT`). |
| `card.asc` | `card` | `card` | `dim_cartao` | $892$ | Cartões de crédito emitidos vinculados a uma disposição. |
| `district.asc` | `district` | `district` | `dim_distrito` | $77$ | Indicadores demográficos e socioeconômicos dos distritos tchecos. |
| `loan.asc` | `loan` | `loan` | `fato_emprestimos` | $682$ | Contratos de empréstimos concedidos e status de adimplência. |
| `order.asc` | `order` | `order` | `fato_ordem` | $6.471$ | Ordens de pagamento permanentes (débitos agendados). |
| `trans.asc` | `trans` | `trans` | `fato_transacoes` e `dim_tipo_transacao` | $1.056.320$ | Histórico completo de movimentações financeiras nas contas. |

---

## 2. Dicionário Detalhado das Dimensões (`portfolio.gold`)

### 2.1. `portfolio.gold.dim_conta` (Origem: `account.asc`)
Armazena as informações cadastrais das contas correntes do banco.

| Coluna Gold / Silver | Coluna Original (Bronze) | Tipo de Dado | Regra de Transformação e Domínio |
| :--- | :--- | :--- | :--- |
| `id_conta` | `account_id` | `INT` | **PK** — Identificador único da conta bancária. |
| `id_distrito` | `district_id` | `INT` | **FK** — Código do distrito onde a agência da conta está localizada. |
| `frequencia_emissao` | `frequency` | `STRING` | Traduzido do tcheco:<br>• `'POPLATEK MESICNE'` $\rightarrow$ `'Emissao Mensal'`<br>• `'POPLATEK TYDNE'` $\rightarrow$ `'Emissao Semanal'`<br>• `'POPLATEK PO OBRATU'` $\rightarrow$ `'Emissao Apos Transacao'` |
| `data_criacao` | `date` | `DATE` | Convertido do formato `YYMMDD` adicionando o prefixo `'19'` (`to_date(concat('19', date), 'yyyyMMdd')`). |

---

### 2.2. `portfolio.gold.dim_cliente` (Origem: `client.asc`)
Contém os atributos demográficos extraídos do documento nacional tcheco (`birth_number`).

| Coluna Gold / Silver | Coluna Original (Bronze) | Tipo de Dado | Regra de Transformação e Domínio |
| :--- | :--- | :--- | :--- |
| `id_cliente` | `client_id` | `INT` | **PK** — Identificador único do cliente (alvo de hash SHA-256 na camada de governança LGPD). |
| `id_distrito` | `district_id` | `INT` | **FK** — Código do distrito de residência do cliente. |
| `genero` | `birth_number` | `STRING` | Extraído dos dígitos de mês (`MM`) de `YYMMDD`:<br>• Se $\text{MM} > 50 \rightarrow$ `'F'` (Feminino)<br>• Caso contrário $\rightarrow$ `'M'` (Masculino) |
| `data_nascimento` | `birth_number` | `DATE` | Reconstruída subtraindo $50$ do mês para mulheres e concatenando o século `'19'` (`YYYY-MM-DD`). |
| `idade` | *(Derivada)* | `INT` | Idade em anos completos calculada em relação à data-base do dataset (`1998-12-31`): $\lfloor \text{datediff}(\text{'1998-12-31'}, \text{data\_nascimento}) / 365.25 \rfloor$. |

---

### 2.3. `portfolio.gold.dim_Disposicao` (Origem: `disp.asc`)
Tabela associativa que resolve o relacionamento $N:M$ entre Clientes e Contas, determinando quem tem poder de solicitar empréstimos ou cartões.

| Coluna Gold / Silver | Coluna Original (Bronze) | Tipo de Dado | Regra de Transformação e Domínio |
| :--- | :--- | :--- | :--- |
| `id_disposicao` | `disp_id` | `INT` | **PK** — Identificador único do vínculo de disposição. |
| `id_cliente` | `client_id` | `INT` | **FK** — Referência ao cliente em `dim_cliente`. |
| `id_conta` | `account_id` | `INT` | **FK** — Referência à conta em `dim_conta`. |
| `tipo_disposicao` | `type` | `STRING` | Papel do cliente na conta:<br>• `'OWNER'` $\rightarrow$ `'Titular'` (único autorizado a pedir empréstimos/cartões)<br>• `'DISPONENT'` $\rightarrow$ `'Dependente / Autorizado'` |

---

### 2.4. `portfolio.gold.dim_cartao` (Origem: `card.asc`)
Catálogo de cartões de crédito emitidos para disponentes titulares.

| Coluna Gold / Silver | Coluna Original (Bronze) | Tipo de Dado | Regra de Transformação e Domínio |
| :--- | :--- | :--- | :--- |
| `id_cartao` | `card_id` | `INT` | **PK** — Identificador único do cartão de crédito. |
| `id_disposicao` | `disp_id` | `INT` | **FK** — Vínculo com `dim_Disposicao`. |
| `tipo_cartao` | `type` | `STRING` | Categoria do produto:<br>• `'junior'` $\rightarrow$ `'Junior'`<br>• `'classic'` $\rightarrow$ `'Classico'`<br>• `'gold'` $\rightarrow$ `'Ouro'` |
| `data_emissao` | `issued` | `DATE` | Data de emissão convertida de `YYMMDD` para `YYYY-MM-DD`. |

---

### 2.5. `portfolio.gold.dim_distrito` (Origem: `district.asc`)
Matriz demográfica e socioeconômica dos $77$ distritos da República Tcheca.

| Coluna Gold / Silver | Coluna Original (Bronze) | Tipo de Dado | Descrição do Indicador Demográfico |
| :--- | :--- | :--- | :--- |
| `id_distrito` | `A1` (`district_id`) | `INT` | **PK** — Código identificador do distrito. |
| `nome_distrito` | `A2` | `STRING` | Nome oficial do distrito (ex.: *Hl.m. Praha*, *Karvina*). |
| `regiao` | `A3` | `STRING` | Macrorregião (ex.: *Prague*, *central Bohemia*, *north Moravia*). |
| `num_habitantes` | `A4` | `INT` | População total residente no distrito. |
| `mun_menos_499` | `A5` | `INT` | Número de municípios com população $< 499$ habitantes. |
| `mun_500_a_1999` | `A6` | `INT` | Número de municípios com população entre $500$ e $1.999$ habitantes. |
| `mun_2000_a_9999` | `A7` | `INT` | Número de municípios com população entre $2.000$ e $9.999$ habitantes. |
| `mun_mais_10000` | `A8` | `INT` | Número de municípios com população $\ge 10.000$ habitantes. |
| `num_cidades` | `A9` | `INT` | Quantidade total de cidades no distrito. |
| `proporcao_urbana` | `A10` | `DOUBLE` | Percentual de habitantes residindo em áreas urbanas ($\%$). |
| `salario_medio` | `A11` | `DOUBLE` | Salário médio mensal dos habitantes do distrito (em Coroas Tchecas — CZK). |
| `taxa_desemprego_95` | `A12` | `DOUBLE` | Taxa de desemprego registrada no ano de $1995$ ($\%$). |
| `taxa_desemprego_96` | `A13` | `DOUBLE` | Taxa de desemprego registrada no ano de $1996$ ($\%$). |
| `num_empresarios_1000_hab` | `A14` | `INT` | Número de empreendedores por grupo de $1.000$ habitantes. |
| `num_crimes_95` | `A15` | `INT` | Total de ocorrências criminais registradas em $1995$. |
| `num_crimes_96` | `A16` | `INT` | Total de ocorrências criminais registradas em $1996$. |

---

### 2.6. `portfolio.gold.dim_tipo_transacao` (Origem: `trans.asc`)
Dimensão gerada via `SELECT DISTINCT` das combinações operacionais de transações para normalizar os domínios de movimentação financeira.

| Coluna Gold | Coluna Original (Bronze) | Tipo de Dado | Regra de Negócio e Domínio Traduzido |
| :--- | :--- | :--- | :--- |
| `id_tipo_transacao` | *(Surrogate Key)* | `BIGINT` / `INT` | **PK** — Chave substituta gerada para identificar a combinação única de tipo, operação e símbolo. |
| `tipo_transacao` | `type` | `STRING` | Natureza contábil da movimentação:<br>• `'PRIJEM'` $\rightarrow$ `'Credito'` (Entrada)<br>• `'VYDAJ'` $\rightarrow$ `'Debito'` / `'Saque'` (Saída)<br>• `'VYBER'` $\rightarrow$ `'Saque em Dinheiro'` |
| `operacao` | `operation` | `STRING` | Modalidade da operação:<br>• `'VYBER KARTOU'` $\rightarrow$ `'Saque com Cartao de Credito'`<br>• `'VKLAD'` $\rightarrow$ `'Deposito em Dinheiro'`<br>• `'PREVOD Z UCTU'` $\rightarrow$ `'Recebimento de Outro Banco'`<br>• `'VYBER'` $\rightarrow$ `'Saque em Dinheiro'`<br>• `'PREVOD NA UCET'` $\rightarrow$ `'Remessa para Outro Banco'` |
| `k_symbol` | `k_symbol` | `STRING` | Finalidade/Caracterização da transação:<br>• `'POJISTNE'` $\rightarrow$ `'Pagamento de Seguro'`<br>• `'SLUZBY'` $\rightarrow$ `'Pagamento por Extrato/Servicos'`<br>• `'UROK'` $\rightarrow$ `'Juros Creditados'`<br>• `'SANKC. UROK'` $\rightarrow$ `'Juros Sancionatorios (Saldo Negativo)'`<br>• `'SIPO'` $\rightarrow$ `'Despesas Domesticas'`<br>• `'DUCHOD'` $\rightarrow$ `'Aposentadoria / Pensao'`<br>• `'UVER'` $\rightarrow$ `'Pagamento de Emprestimo'` |

---

## 3. Dicionário Detalhado das Tabelas Fato (`portfolio.gold`)

### 3.1. `portfolio.gold.fato_transacoes` (Origem: `trans.asc`)
Tabela fato transacional granular contendo $1.056.320$ registros de movimentações financeiras.

| Coluna Gold / Silver | Coluna Original (Bronze) | Tipo de Dado | Descrição e Regra de Negócio |
| :--- | :--- | :--- | :--- |
| `id_transacao` | `trans_id` | `INT` | **PK** — Identificador único da transação. |
| `id_conta` | `account_id` | `INT` | **FK** — Conta associada à movimentação (`dim_conta`). |
| `id_tipo_transacao` | *(Chave Composta)* | `INT` | **FK** — Referência à modalidade em `dim_tipo_transacao`. |
| `data_transacao` | `date` | `DATE` | Data de efetivação da transação (`YYYY-MM-DD`). |
| `valor` | `amount` | `DOUBLE` | Valor financeiro movimentado na operação (sempre positivo na origem). |
| `saldo_apos_transacao` | `balance` | `DOUBLE` | Saldo remanescente na conta imediatamente após a transação (pode assumir valores negativos). |
| `banco_parceiro` | `bank` | `STRING` | Código de duas letras do banco da contraparte (quando aplicável). |
| `conta_parceiro` | `account` | `STRING` | Número da conta da contraparte (quando aplicável). |

---

### 3.2. `portfolio.gold.fato_emprestimos` (Origem: `loan.asc`)
Tabela fato acumulada que registra os contratos de crédito bancário ($682$ contratos).

| Coluna Gold / Silver | Coluna Original (Bronze) | Tipo de Dado | Descrição e Regra de Negócio |
| :--- | :--- | :--- | :--- |
| `id_emprestimo` | `loan_id` | `INT` | **PK** — Identificador único do contrato de empréstimo. |
| `id_conta` | `account_id` | `INT` | **FK** — Conta recebedora do empréstimo (`dim_conta`). |
| `data_concessao` | `date` | `DATE` | Data em que o empréstimo foi concedido (`YYYY-MM-DD`). |
| `valor_emprestimo` | `amount` | `DOUBLE` | Montante principal total contratado. |
| `duracao_meses` | `duration` | `INT` | Prazo total do contrato em meses ($12, 24, 36, 48$ ou $60$ meses). |
| `valor_pagamento_mensal` | `payments` | `DOUBLE` | Valor fixo da prestação mensal acordada. |
| `status_emprestimo` | `status` | `STRING` | Classificação de performance de crédito:<br>• `'A'` $\rightarrow$ Contrato encerrado, sem problemas (Adimplente)<br>• `'B'` $\rightarrow$ Contrato encerrado, empréstimo não pago (Inadimplente)<br>• `'C'` $\rightarrow$ Contrato em andamento, pagamentos em dia (Adimplente)<br>• `'D'` $\rightarrow$ Contrato em andamento, cliente em dívida (Inadimplente) |

---

### 3.3. `portfolio.gold.fato_ordem` (Origem: `order.asc`)
Tabela fato de agendamentos permanentes de débito configurados pelas contas.

| Coluna Gold / Silver | Coluna Original (Bronze) | Tipo de Dado | Descrição e Regra de Negócio |
| :--- | :--- | :--- | :--- |
| `id_ordem` | `order_id` | `INT` | **PK** — Identificador único da ordem permanente. |
| `id_conta` | `account_id` | `INT` | **FK** — Conta originadora do débito (`dim_conta`). |
| `banco_destino` | `bank_to` | `STRING` | Código de duas letras do banco destinatário. |
| `conta_destino` | `account_to` | `STRING` | Identificador da conta destinatária. |
| `valor_ordem` | `amount` | `DOUBLE` | Valor fixo agendado para transferência recorrente. |
| `finalidade_ordem` | `k_symbol` | `STRING` | Categoria da despesa recorrente (`'SIPO'` $\rightarrow$ Despesas Domésticas, `'UVER'` $\rightarrow$ Empréstimo, `'POJISTNE'` $\rightarrow$ Seguro, `'LEASING'` $\rightarrow$ Leasing). |

---

## 4. Metadados de Auditoria e Linhagem (Bronze & Silver)

Todas as tabelas das camadas intermediárias contam com colunas técnicas de rastreabilidade que são filtradas na visão analítica final (`SELECT * EXCEPT (...)`):
* `data_ingestao_bronze` (`TIMESTAMP`): Data e hora exatas da leitura do arquivo `.asc` a partir do Volume `/Volumes/portfolio/filestore/tables`.
* `data_processamento_silver` (`TIMESTAMP`): Data e hora da aplicação das regras de tipagem, limpeza de strings e tradução de domínios na camada Silver.