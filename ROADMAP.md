# Roadmap Técnico — dados-br

Este documento descreve a visão de evolução técnica do dados-br.
Contribuições são bem-vindas em qualquer etapa.

---

## v0.1.0 — MVP (lançado em 2025)

**Catálogo de datasets**
- [x] 35 datasets declarativos em YAML, organizados por fonte e categoria
- [x] Fontes: INEP/MEC, IBGE, DATASUS, Tesouro Nacional/FNDE, CGU, TCU, CNJ, CNMP, MPF, CNPq, CAPES, INPI, MCTI, UFRN, Prefeituras (SP, Rio, Goiânia), Goiás, SNIS
- [x] Modelos Pydantic v2 com validação completa por url_type
- [x] Registry com carregamento lazy e busca por categoria, id, texto
- [x] Suporte a url_type: pattern (série histórica), static_list, dynamic, ftp

**CLI (dados-br)**
- [x] Subcomandos: list, info, download, check, catalog, indicators
- [x] Modo interativo guiado (categorias → datasets → anos)
- [x] Progress bars e spinners (Rich)
- [x] Estimativa de tamanho antes do download (download + extração)
- [x] Verificação de espaço em disco disponível
- [x] Dry-run (`--dry-run`)

**Download e validação**
- [x] Download HTTP com retry/backoff e resume parcial
- [x] Download FTP via urllib (DATASUS, DBC)
- [x] Extração ZIP com validação de integridade
- [x] Checagens: file_exists, zip_valid, min_size_mb, csv_readable, row_count, dbc_exists

**Módulo de indicadores** _(diferencial para pesquisa)_
- [x] 38 indicadores educacionais e sociais organizados em 6 arquivos YAML
- [x] Níveis: educação básica (15), educação superior (4), transversal (19)
- [x] 155+ perguntas norteadoras para orientar pesquisas
- [x] 123+ referências bibliográficas em ABNT
- [x] CLI: `indicators list`, `indicators info`, `indicators questions`, `indicators for-dataset`, `indicators validate`
- [x] API Python: `IndicatorRegistry` com busca por nível, categoria, dataset, texto

**Cobertura de indicadores por dataset (100%)**
- [x] Todos os 35 datasets do catálogo têm ao menos um indicador associado

**Infraestrutura**
- [x] Testes pytest (models, registry, checker, yamls, CLI)
- [x] GitHub Actions CI (lint + typecheck + testes + validação catálogo)
- [x] GitHub Actions Release (build + PyPI via hatch)
- [x] Licença Apache 2.0
- [x] Documentação: README, CONTRIBUTING, ROADMAP

---

## v0.2.0 — Expansão e Qualidade

**Catálogo**
- [ ] Adicionar RAIS (emprego formal, MTE/CAGED)
- [ ] Adicionar PISA (OCDE — arquivos públicos)
- [ ] Adicionar CNIS (previdência social, INSS)
- [ ] Suporte a datasets de outros estados além de Goiás (TCE estaduais)
- [ ] Versionamento do schema YAML (`_schema_version`)

**Downloader**
- [ ] Download paralelo/assíncrono com httpx async
- [ ] Detecção automática de atualizações (Last-Modified header)
- [ ] Cálculo de hash MD5/SHA256 para verificação de integridade
- [ ] Modo `--since YYYY-MM-DD`: baixa apenas arquivos modificados
- [ ] Suporte a autenticação básica (user:pass) para fontes protegidas

**UX**
- [ ] `--output-format json` para integração com scripts e pipelines
- [ ] Comando `dados-br status` — resumo de downloads e última checagem
- [ ] Suporte a arquivo de configuração `~/.dados-br.toml`
- [ ] Autocompletion de IDs de datasets no shell (bash/zsh/fish)

---

## v0.3.0 — Pipeline de Dados

**Transformação**
- [ ] Módulo `dadosbr.transform` com leitores padronizados por dataset
- [ ] Conversão automática de microdados INEP CSV → Parquet
- [ ] Conversão de DBC (DATASUS) → Parquet via `pysus`
- [ ] Normalização de encodings (ISO-8859-1, UTF-8) e separadores
- [ ] Dicionário de variáveis machine-readable por dataset (YAML)

**DuckDB Integration**
- [ ] Comando `dados-br query <dataset> "<SQL>"` — query direta via DuckDB
- [ ] Registro automático de Parquets no DuckDB como views
- [ ] Exportação para CSV, Parquet, JSON, Excel via CLI

**PyArrow**
- [ ] Schema Arrow por dataset para leitura eficiente e tipagem correta
- [ ] Suporte a particionamento por ano/UF para grandes datasets

---

## v0.4.0 — Cálculo de Indicadores

**Engine de cálculo**
- [ ] Módulo `dadosbr.compute` para cálculo programático dos indicadores
- [ ] IDEB calculado (SAEB + Censo Escolar)
- [ ] Taxa de Distorção Idade-Série calculada por escola/município
- [ ] Gasto por aluno calculado (SIOPE + Censo Escolar)
- [ ] Mortalidade infantil calculada (SIM + SINASC + IBGE populações)
- [ ] Taxa de analfabetismo funcional por município (PNADc)

**Validação estatística**
- [ ] Testes de consistência entre bases (ex: Censo Escolar × ENEM)
- [ ] Detecção de outliers em séries históricas
- [ ] Relatório de qualidade por dataset

---

## v0.5.0 — Ecossistema e Comunidade

**SDK Python**
- [ ] API programática estável (`from dadosbr import download, load, compute`)
- [ ] Suporte a Jupyter Notebook com widgets interativos (ipywidgets)
- [ ] Integração com `ydata-profiling` para EDA automatizada

**Documentação**
- [ ] Documentação completa com MkDocs Material (hospedada no GitHub Pages)
- [ ] Tutoriais por caso de uso (IDEB, saúde infantil, financiamento educacional)
- [ ] Galeria de notebooks Jupyter de análise
- [ ] Referência completa da API

**Plugin System**
- [ ] Sistema de plugins para fontes de dados customizadas
- [ ] Plugin para dados municipais do TCE-GO, TCE-SP, etc.
- [ ] Plugin para portais CKAN (dados.gov.br, portais estaduais)

**Qualidade**
- [ ] Link checker automatizado mensal (GitHub Actions)
- [ ] Alertas via GitHub Issues quando URLs quebrarem
- [ ] Relatório de disponibilidade dos datasets

---

## Considerações de Arquitetura

### Async-first (v0.3+)
Migrar o downloader para `httpx.AsyncClient` com `asyncio` para downloads paralelos,
mantendo compatibilidade síncrona via `asyncio.run()`.

### Schema Evolution
Versionar o schema YAML para migrações sem quebrar backward compatibility:
```yaml
_schema_version: "2"
id: enem
```

### Federação de Catálogos
Permitir múltiplos catálogos remotos (GitHub, GitLab) além do catálogo local,
similar ao sistema de remotes do git.

---

*Último update: março de 2025. Para sugerir itens no roadmap, abra uma issue com a tag `roadmap`.*
