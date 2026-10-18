# Planejamento Ágil e Gestão de Sprints — Portfólio Engenharia & Ciência de Dados

## 1. Metodologia e Governança Ágil
O projeto adota o framework **Scrum combinado ao Kanban (Scrumban)**, estruturado em **4 Sprints de 1 semana**, cobrindo as 9 etapas da arquitetura ponta a ponta sobre o **Berka Dataset (PKDD'99)**.

### Definition of Done (DoD — Definição de Pronto)
Uma User Story só é considerada concluída (`DONE`) quando:
1. O código segue boas práticas de modularização (PEP8 / PySpark Standards) e está versionado no repositório.
2. Os dados processados possuem validação de schema, tipagem forte e ausência de quebras nas chaves primárias/estrangeiras.
3. A documentação técnica correspondente (`docs/`) está atualizada.
4. Os testes automatizados (`pytest`) executam sem erros.

---

## 2. Visão Geral dos Épicos

| ID | Épico | Etapas Cobertas | Story Points Totais | Status Geral |
| :---: | :--- | :---: | :---: | :--- |
| **EP-01** | Fundamentos de Negócio, Infraestrutura e Ingestão | Etapas 1, 2 e 3 | $21$ pts | 🟡 Em Andamento |
| **EP-02** | Arquitetura Lakehouse (Medalhão) e Governança LGPD | Etapas 4 e 6 | $26$ pts | 🟡 Em Andamento |
| **EP-03** | Análise Exploratória (EDA), Estatística e SQL Avançado | Etapas 5 e 7 | $21$ pts | 🟢 Avançado |
| **EP-04** | MLOps/DataOps (Airflow, CI/CD) e Data Storytelling (BI/App) | Etapas 8 e 9 | $21$ pts | ⚪ Backlog |

---

## 3. Quadro Kanban Atualizado (Status Real do Projeto)

### ✅ DONE (Concluído)
* **[US-01] Planejamento de Negócio, KPIs e Dicionário de Dados (`Etapa 1`)** — *5 pts*
  * *Entrega:* `docs/business_case_kpis.md`, `docs/data_dictionary.md` e `docs/agile_sprint_board.md`.
* **[US-05] Ingestão Automatizada de Arquivos `.asc` para Camada Bronze (`Etapa 3 / Etapa 6`)** — *5 pts*
  * *Entrega:* Notebook `00_carregar_csv_bronze` ingerindo as 8 tabelas no Unity Catalog (`portfolio.bronze`) com carimbo `data_ingestao_bronze`.
* **[US-08] Padronização, Tradução e Decodificação Demográfica na Camada Silver (`Etapa 6`)** — *8 pts*
  * *Entrega:* Transformação das tabelas no schema `portfolio.silver`, extração de `genero`, `data_nascimento` e `idade` a partir de `birth_number` e tradução dos domínios tchecos.
* **[US-09] Modelagem Dimensional Star Schema na Camada Gold (`Etapa 6`)** — *8 pts*
  * *Entrega:* Criação das 6 Dimensões e 3 Tabelas Fato no schema `portfolio.gold`.
* **[US-11] Estatística Descritiva Profissional e Detecção de Outliers via IQR (`Etapa 5`)** — *8 pts*
  * *Entrega:* Funções `descritivas_profissional` (Média, DP, CV, Quartis, Assimetria e Curtose em `fato_transacoes`) e `flag_outliers` (IQR em `fato_emprestimos`).

### 🔄 IN PROGRESS (Em Progresso)
* **[US-12] Correlações Visuais e Relatórios Automatizados de Profiling (`Etapa 5`)** — *5 pts*
  * *Tarefas:* Gerar `notebooks/02_correlacoes_visuais.ipynb` (Seaborn/Matplotlib) e exportar relatórios HTML (`Sweetviz` / `YData Profiling`) na pasta `reports/`.
* **[US-10] Implementação de Slowly Changing Dimensions — SCD Tipo 2 (`Etapa 6`)** — *5 pts*
  * *Tarefas:* Criar `sql/ddl_olap_dw/dim_clientes_scd2.sql` e `src/transformation/scd_incremental_load.py` com controle de `data_inicio_vigencia`, `data_fim_vigencia` e `flag_ativo`.

### 📋 TO DO (Backlog Priorizado)
* **[US-06] Governança de Dados: Anonimização LGPD e Auditoria de Viés (`Etapa 4`)** — *8 pts*
  * *Tarefas:* Implementar `src/governance/lgpd_anonymizer.py` (hash SHA-256 em dados sensíveis) e `src/governance/bias_auditor.py` (teste estatístico de equidade de gênero/idade na emissão de cartões e empréstimos).
* **[US-13] Consultas Analíticas Avançadas com Window Functions e CTEs (`Etapa 7`)** — *5 pts*
  * *Tarefas:* Criar `sql/analytics_queries/cohort_retention.sql` e `sql/analytics_queries/ranking_faturamento.sql`.
* **[US-02] Infraestrutura como Código (Docker & Terraform) e Modelagem 3FN (`Etapa 2`)** — *8 pts*
  * *Tarefas:* Criar `infra/docker/`, `infra/terraform/` e `sql/ddl_oltp/create_tables_3nf.sql`.
* **[US-04] Modularização da Ingestão Poliglota em Scripts Python (`Etapa 3`)** — *5 pts*
  * *Tarefas:* Estruturar conectores em `src/database/` e extratores em `src/ingestion/`.
* **[US-14] Orquestração com Apache Airflow, Testes Pytest e CI/CD (`Etapa 8`)** — *13 pts*
  * *Tarefas:* Criar DAG `dags/pipeline_dados_dag.py`, suíte `tests/` e workflow `.github/workflows/ci_pipeline.yml`.
* **[US-15] Dashboard Executivo e Data App Interativo em Streamlit (`Etapa 9`)** — *8 pts*
  * *Tarefas:* Desenvolver `app/streamlit_app.py` e documentar `bi/ux_ui_wireframe.md`.

---

## 4. Cronograma de Sprints (Roadmap de Execução)

| Sprint | Foco Principal | Entregáveis-Chave | Meta da Sprint |
| :---: | :--- | :--- | :--- |
| **Sprint 1** | Negócio, Lakehouse Core & EDA Estatística | `docs/*.md`, Camadas Bronze/Silver/Gold no Databricks, Estatística Descritiva + IQR | Ter os dados limpos, modelados em Star Schema e documentados. **(Concluída)** |
| **Sprint 2** | Governança LGPD, Visualização, SCD2 e SQL Analítico | `lgpd_anonymizer.py`, `bias_auditor.py`, `dim_clientes_scd2.sql`, `02_correlacoes_visuais.ipynb`, Queries SQL | Garantir conformidade legal, rastreabilidade histórica (SCD2) e insights visuais. |
| **Sprint 3** | IaC, Bancos OLTP/NoSQL e Modularização Python | `Dockerfile`, `main.tf`, `create_tables_3nf.sql`, módulos em `src/database/` e `src/ingestion/` | Desacoplar a lógica de notebooks para pacotes Python reprodutíveis em containers. |
| **Sprint 4** | Automação DataOps (Airflow + CI/CD) e Consumo (Streamlit/BI) | `pipeline_dados_dag.py`, `test_data_quality.py`, `ci_pipeline.yml`, `streamlit_app.py` | Orquestrar o pipeline de ponta a ponta e entregar a camada de decisão executiva. |