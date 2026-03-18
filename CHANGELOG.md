# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.

O formato segue o padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [Não lançado]

---

## [0.1.0] — 2026-03-17

Primeira versão estável do **dados-br**. Cobre o ciclo completo de trabalho com
dados públicos brasileiros: descoberta, download, validação e contextualização
para pesquisa.

### Adicionado

#### Catálogo declarativo (36 datasets)
- Estrutura de catálogo em YAML versionado, organizado por fonte e categoria
- 36 datasets cobrindo educação, saúde, finanças públicas, transparência, ciência e municípios
- Suporte a quatro tipos de URL: `pattern` (série histórica por ano), `static_list` (arquivos avulsos), `dynamic` (descoberta via scraping) e `ftp`
- Validação de schema via Pydantic v2 no momento do carregamento
- Datasets incluídos: ENEM, Censo Escolar, Censo da Educação Superior, SAEB, ENCCEJA, IDEB (série histórica 2005–2023), Taxas de Distorção Idade-Série (INEP), CAPES Sucupira, UFRN Dados Abertos, PNAD Contínua, Censo Demográfico 2010/2022, PeNSE, Malhas Territoriais IBGE, SIM (óbitos adultos e infantis), SINASC, Estimativas Populacionais (DATASUS), SIOPE, Tesouro Transparente, Portal da Transparência Federal, CGU (acordos de leniência), TCU Acórdãos, CNJ Justiça em Números, CNMP, MPF, CNPq Bolsas e Grupos, INPI Patentes, MCTI Indicadores, Prefeituras SP/Rio/Goiânia, SEDUC-GO, SES-GO, AGR-GO (saneamento), SNIS Resíduos Sólidos

#### CLI (`dados-br`)
- Comando `dados-br list` — lista datasets com filtros por categoria, fonte e busca textual; flag `--commands` exibe o comando de download de cada dataset
- Comando `dados-br info <id>` — exibe metadados completos de um dataset (descrição, fonte, categoria, anos disponíveis, tamanho estimado, checks)
- Comando `dados-br download [id]` — download com barra de progresso, retry automático, resume de interrupções e suporte a HTTP e FTP; modo interativo quando chamado sem argumentos; flag `--dry-run` simula sem baixar; flag `--years` para selecionar anos específicos
- Comando `dados-br check [id]` — valida integridade de arquivos baixados (existência, ZIP válido, tamanho mínimo, contagem de linhas CSV)
- Comando `dados-br catalog validate` — valida todos os YAMLs do catálogo
- Comando `dados-br catalog stats` — exibe estatísticas do catálogo (total de datasets, categorias, tamanho estimado)
- Comando `dados-br indicators list` — lista indicadores com filtros por nível (`--level`) e categoria (`--category`)
- Comando `dados-br indicators info <id>` — exibe descrição metodológica, fórmula, periodicidade, desagregações, citações ABNT e perguntas norteadoras
- Comando `dados-br indicators questions` — lista perguntas norteadoras filtradas por dataset (`--dataset`) ou nível
- Comando `dados-br indicators for-dataset <id>` — lista indicadores relacionados a um dataset específico

#### Módulo de indicadores (38 indicadores)
- 38 indicadores educacionais e sociais com descrição metodológica detalhada
- 155 perguntas norteadoras para orientar análises e pesquisas
- Referências bibliográficas completas em formato ABNT
- Indicadores organizados em 6 arquivos YAML: educação básica, educação superior, IBGE social, DATASUS saúde, financeiro-educação e transversais
- Cobertura de 100% dos datasets do catálogo por pelo menos um indicador

#### Engine de download
- Download via `httpx` com retry exponencial e timeout configurável
- Suporte a FTP (via `urllib.request`) para bases do DATASUS e outras fontes legadas
- Estimativa de tamanho antes do download (MB por ano e total)
- Resume automático de downloads interrompidos (verificação de arquivo existente)
- Modo dry-run para simulação sem transferência de dados

#### Validação pós-download (`checker`)
- Checagem `file_exists` — confirma presença do arquivo
- Checagem `zip_valid` — abre e lista conteúdo do ZIP sem extrair
- Checagem `min_size_mb` — valida tamanho mínimo configurável
- Checagem `csv_readable` — lê o CSV e confirma número mínimo de linhas
- Relatório estruturado com contagem de verificações aprovadas e falhas

#### Testes automatizados (507 testes)
- Testes unitários dos modelos Pydantic
- Testes parametrizados de todos os YAMLs do catálogo
- Testes do registry de datasets (carregamento, busca, filtragem)
- Testes do checker (todas as checagens)
- Testes da CLI via Typer `CliRunner`
- Testes do registry de indicadores (40+ casos)
- CI no GitHub Actions: lint (ruff), typecheck (mypy) e testes em Python 3.11 e 3.12

---

[Não lançado]: https://github.com/tucaguimaraes/dados-br/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tucaguimaraes/dados-br/releases/tag/v0.1.0
