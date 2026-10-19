## Descrição da Entrega (Pull Request)
Descreva de forma objetiva qual funcionalidade, tabela ou pipeline foi adicionado/alterado neste PR.

## Camada da Arquitetura Afetada
- [ ] Infraestrutura / Docker / Terraform (`infra/`)
- [ ] Ingestão / Camada Bronze (`src/ingestion/` | `portfolio.bronze`)
- [ ] Governança / LGPD / Viés (`src/governance/`)
- [ ] Transformação / Camada Silver (`src/transformation/` | `portfolio.silver`)
- [ ] Modelagem Star Schema / Camada Gold / SCD2 (`sql/` | `portfolio.gold`)
- [ ] BI / UX-UI / Data App Streamlit (`bi/` | `app/`)

## Checklist de Governança e Qualidade (Definition of Done)
- [ ] Todos os testes unitários (`pytest tests/`) passaram no GitHub Actions.
- [ ] Nenhum dado sensível (`birth_number`, CPF, senhas ou `.env`) está exposto em texto aberto.
- [ ] As consultas SQL seguem os padrões do Unity Catalog (`portfolio.gold`).
- [ ] A documentação correspondente na pasta `docs/` foi atualizada.