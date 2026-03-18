# Guia de Contribuição — dados-br

Obrigado por considerar contribuir com o dados-br! Este projeto nasceu do esforço de um pesquisador goiano e cresce com a colaboração da comunidade brasileira de dados abertos.

---

## Como contribuir

### 1. Reportar problemas (Issues)

Antes de abrir uma issue, verifique se já existe uma similar. Ao reportar, inclua:

- Versão do dados-br (`dados-br version`)
- Sistema operacional e versão do Python
- Comando executado e mensagem de erro completa
- Dataset afetado (se aplicável)

### 2. Sugerir novos datasets

Para propor uma nova base de dados, abra uma issue com a tag `novo-dataset` contendo:

- Nome completo e descrição da base
- Órgão/entidade responsável e URL de acesso
- Formato dos arquivos (ZIP, CSV, DBC...)
- Periodicidade de atualização
- Indicadores e análises que ela permite

### 3. Contribuir com código

#### Configurando o ambiente

```bash
# Clone o repositório
git clone https://github.com/tucaguimaraes/dados-br.git
cd dados-br

# Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate     # Linux/Mac
# .venv\Scripts\activate      # Windows

# Instale em modo editável com dependências de dev
pip install -e ".[dev]"

# Verifique a instalação
pytest tests/ -m "not integration"
dados-br --help
dados-br catalog validate
```

#### Adicionando um dataset ao catálogo

1. Crie `catalog/<categoria>/<id>.yaml` seguindo o schema abaixo
2. Valide: `dados-br catalog validate`
3. Rode os testes: `pytest tests/test_yamls.py -v`
4. Abra o Pull Request

**Schema para `url_type: pattern` (série histórica por ano):**
```yaml
id: meu_dataset           # snake_case único, sem espaços
name: "Nome Legível do Dataset"
source: "Órgão Responsável"
category: educacao        # educacao|saude|demografico|financeiro|transparencia|...
description: |
  Descrição completa do dataset. Mínimo 10 caracteres.
  Inclua o que os dados contêm e para que servem.
tags: [tag1, tag2]
license: "Dados Abertos"
homepage: "https://www.gov.br/..."
url_type: pattern
file_format: zip
years:
  start: 2010
  end: 2024
url_pattern: "https://fonte.gov.br/dados_{year}.zip"
est_size_mb_per_year: 50
est_extracted_mb_per_year: 200
dest_folder: "orgao/meu_dataset"
checks:
  - type: file_exists
  - type: zip_valid
  - type: min_size_mb
    value: 10
```

**Schema para `url_type: static_list` (arquivos avulsos):**
```yaml
id: meu_dataset_estatico
name: "Dataset com Arquivos Específicos"
source: "Órgão"
category: transparencia
description: |
  Descrição.
url_type: static_list
file_format: csv
files:
  - url: "https://dados.gov.br/arquivo_2023.csv"
    filename: "arquivo_2023.csv"
    description: "Dados de 2023"
    est_size_mb: 80
    year: 2023
est_size_mb_total: 80
dest_folder: "orgao/dataset_estatico"
checks:
  - type: file_exists
  - type: csv_readable
```

#### Adicionando um indicador

Indicadores ficam em `catalog/indicators/`. Para adicionar a um arquivo existente ou criar um novo:

```yaml
# Em catalog/indicators/<arquivo>.yaml, dentro de `indicators:`
- id: meu_indicador
  name: "Nome Completo do Indicador"
  category: desempenho      # desempenho|fluxo|docentes|escola|financeiro|...
  description: |
    Descrição metodológica detalhada.
  periodicity: anual
  available_since: 2007
  methodology_url: "https://..."
  disaggregations:
    - municipio
    - estado
    - brasil
  source_datasets:
    - censo_escolar
    - saeb
  citations:
    - "AUTOR, N. Título. Local: Editora, ano."
  research_questions:
    - "Pergunta norteadora para orientar a análise do indicador?"
    - "Segunda pergunta com hipótese investigável a partir dos dados?"
```

Valide com: `dados-br indicators validate`

#### Convenções de código

- **Formatação:** `ruff check dadosbr/ tests/` e `ruff format .`
- **Tipos:** type hints obrigatórios em funções públicas
- **Docstrings:** estilo Google para funções públicas
- **Commits:** em português, prefixados com `feat:`, `fix:`, `docs:`, `test:`, `chore:`
- **Branches:** `feat/nome-da-feature`, `fix/descricao-do-bug`, `docs/o-que-documenta`

#### Rodando os testes

```bash
# Testes unitários (sem acesso à internet)
pytest tests/ -m "not integration" -v

# Com cobertura de código
pytest tests/ -m "not integration" --cov=dadosbr --cov-report=term-missing

# Validar catálogo YAML
dados-br catalog validate

# Validar indicadores
dados-br indicators validate

# Arquivo específico
pytest tests/test_yamls.py -v
pytest tests/test_cli.py -v
```

#### Abrindo um Pull Request

1. Faça fork do repositório
2. Crie uma branch: `git checkout -b feat/minha-contribuicao`
3. Faça suas alterações e testes locais
4. Execute linters e testes: `ruff check . && pytest tests/ -m "not integration"`
5. Commite com mensagem clara descrevendo o que e por quê
6. Abra o PR descrevendo a mudança, a motivação e como testar

### 4. Melhorar a documentação

Documentação clara e precisa é tão valiosa quanto código. Você pode:

- Corrigir erros ou ambiguidades no README
- Melhorar descrições de datasets no YAML (mais contexto, mais uso esperado)
- Adicionar perguntas norteadoras a indicadores existentes
- Adicionar referências bibliográficas novas
- Criar tutoriais de análise em Jupyter Notebook

---

## Estrutura do projeto

```
dados-br/
├── dadosbr/               # Pacote Python principal
│   ├── cli.py             # CLI (Typer + Rich)
│   ├── models.py          # Modelos Pydantic do catálogo
│   ├── registry.py        # Registry de datasets (carregamento lazy)
│   ├── indicators.py      # Registry de indicadores e perguntas norteadoras
│   ├── downloader.py      # Engine de download (httpx + urllib FTP)
│   ├── extractor.py       # Extração de ZIPs
│   ├── checker.py         # Checagens de integridade pós-download
│   └── utils.py           # Utilitários compartilhados
├── catalog/               # Catálogo declarativo em YAML
│   ├── <fonte>/           # Uma pasta por fonte (inep_mec, ibge, datasus, ...)
│   └── indicators/        # Indicadores com citações e perguntas norteadoras
├── tests/                 # Testes pytest
│   ├── conftest.py        # Fixtures compartilhadas
│   ├── test_models.py     # Testes de modelos Pydantic
│   ├── test_registry.py   # Testes do registry
│   ├── test_checker.py    # Testes das checagens
│   ├── test_yamls.py      # Testes parametrizados dos YAMLs
│   └── test_cli.py        # Testes da CLI (Typer TestClient)
└── .github/workflows/     # GitHub Actions
    ├── ci.yml             # lint + typecheck + testes + validação catálogo
    └── release.yml        # build + GitHub Release + publicação PyPI
```

---

## Código de Conduta

Este projeto adota o [Contributor Covenant](https://www.contributor-covenant.org/).
Seja respeitoso, inclusivo e construtivo. Dados públicos são um bem coletivo — vamos tratá-los assim.

---

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a [Apache License 2.0](LICENSE), a mesma licença do projeto.
