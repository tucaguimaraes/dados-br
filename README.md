# dados-br

> Ferramenta open source para catalogar, baixar, validar e analisar dados públicos brasileiros — com indicadores, citações e perguntas norteadoras para pesquisa.

[![CI](https://github.com/tucaguimaraes/dados-br/actions/workflows/ci.yml/badge.svg)](https://github.com/tucaguimaraes/dados-br/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/dados-br.svg)](https://pypi.org/project/dados-br/)

---

## Sobre o projeto

**dados-br** nasceu da necessidade real de um pesquisador e gestor público de reunir, em um único lugar, as principais bases de dados abertas do governo brasileiro para análise educacional, social e de transparência.

O projeto teve origem em 2024 com scripts Python desenvolvidos por **Carlos Artur Guimarães** para automatizar o download e cruzamento de bases do INEP, IBGE e DATASUS em pesquisas sobre educação no estado de Goiás. Ao longo do desenvolvimento, a ferramenta foi evoluindo — com apoio de IA generativa — para uma arquitetura declarativa, extensível e publicável como software livre.

O objetivo é democratizar o acesso a dados públicos brasileiros para pesquisadores, jornalistas de dados, gestores públicos e desenvolvedores, eliminando a barreira técnica de localizar, baixar e validar dezenas de bases dispersas em portais governamentais.

---

## O que o dados-br faz

- 📋 **Catálogo declarativo** — 36+ datasets em YAML versionado, organizados por fonte e categoria
- ⬇️ **Download inteligente** — progress bar, retry automático, resume de interrupções, suporte a HTTP e FTP
- ✅ **Validação automática** — checagens de integridade após download (ZIP, CSV, tamanho mínimo, contagem de linhas)
- 📊 **Indicadores com contexto** — 38 indicadores educacionais e sociais com citações bibliográficas (ABNT) e perguntas norteadoras para pesquisa
- 🔍 **Modo interativo** — seleção guiada de categorias, datasets e anos sem precisar memorizar IDs
- 💡 **Estimativa prévia** — tamanho de download e espaço necessário após extração antes de iniciar

---

## Instalação

```bash
pip install dados-br
```

**Do repositório (modo desenvolvimento):**
```bash
git clone https://github.com/tucaguimaraes/dados-br.git
cd dados-br
pip install -e ".[dev]"
```

Requisitos: Python 3.11+

---

## Uso rápido

```bash
# Explorar o catálogo
dados-br list
dados-br list --category educacao
dados-br list --search "transparencia"
dados-br info enem
dados-br info siope

# Download por anos
dados-br download enem --years 2021-2023
dados-br download censo_escolar --years 2020,2022,2023
dados-br download siope

# Modo interativo (sem argumentos — recomendado para explorar)
dados-br download

# Dry-run: simula sem baixar
dados-br download cnpq_bolsas_fomentos --dry-run

# Verificar integridade dos arquivos baixados
dados-br check enem --dir ./dados
dados-br check

# Catálogo
dados-br catalog validate
dados-br catalog stats
```

---

## Indicadores e perguntas norteadoras

O módulo de indicadores é o diferencial do dados-br para uso em pesquisa. Cada indicador traz:
- descrição metodológica detalhada
- referências bibliográficas em ABNT
- perguntas norteadoras para orientar análises

```bash
# Listar todos os 38 indicadores
dados-br indicators list

# Filtrar por nível de ensino
dados-br indicators list --level basica
dados-br indicators list --level superior

# Ver detalhes completos de um indicador: descrição, fórmula, citações e perguntas
dados-br indicators info ideb
dados-br indicators info gasto_aluno_municipio
dados-br indicators info mortalidade_infantil

# Ver todas as perguntas norteadoras de uma base
dados-br indicators questions --dataset censo_escolar
dados-br indicators questions --dataset siope
dados-br indicators questions --level basica --category docentes

# Indicadores relacionados a um dataset
dados-br indicators for-dataset saeb
dados-br indicators for-dataset sinasc
```

**Exemplo de saída de `dados-br indicators info ideb`:**

```
┌─────────────────────────────────────────────────────────────────┐
│  ideb                                                           │
│  IDEB – Índice de Desenvolvimento da Educação Básica            │
│  📚 Educação Básica  📊 desempenho  bienal  desde 2005          │
└─────────────────────────────────────────────────────────────────┘

Fórmula: IDEB = N × P

❓ Perguntas Norteadoras para Pesquisa (6 perguntas)
  1. Como o IDEB evoluiu nas escolas públicas estaduais e municipais...
  2. Existe correlação entre o IDEB e o Nível Socioeconômico (Inse)?
  3. Quais municípios atingiram as metas projetadas pelo PNE?
  ...

📚 Referências Bibliográficas (ABNT)
  • FERNANDES, R. Índice de Desenvolvimento da Educação Básica. INEP, 2007.
  • SOARES, J. F.; XAVIER, F. P. Pressupostos educacionais e estatísticos do IDEB. 2013.
  ...
```

---

## Catálogo de datasets (36 bases)

### 🎓 Educação (INEP/MEC + UFRN)

| ID | Dataset | Fonte | Tipo |
|---|---|---|---|
| `enem` | ENEM – Microdados | INEP/MEC | padrão anual |
| `censo_escolar` | Censo Escolar da Educação Básica | INEP/MEC | padrão anual |
| `censo_superior` | Censo da Educação Superior | INEP/MEC | padrão anual |
| `saeb` | SAEB – Avaliação da Educação Básica | INEP/MEC | bienal |
| `encceja` | ENCCEJA | INEP/MEC | lista estática |
| `inep_tdi` | Taxas de Distorção Idade-Série | INEP/MEC | padrão anual |
| `ufrn_dados_abertos` | UFRN – Dados Abertos Acadêmicos | UFRN | dinâmico |
| `ideb` | IDEB – Índice de Desenvolvimento da Educação Básica | INEP/MEC | bienal (2005–2023) |
| `capes_pos_graduacao` | CAPES Sucupira – Pós-Graduação | CAPES/MEC | padrão anual |

### 🗂️ IBGE

| ID | Dataset | Descrição |
|---|---|---|
| `pnadc_microdados` | PNAD Contínua – Microdados Trimestrais | Mercado de trabalho, renda, educação |
| `censo_demografico` | Censo Demográfico 2010 e 2022 | Alfabetização, instrução, frequência por município |
| `pense` | PeNSE – Saúde do Escolar | Saúde, violência e comportamento de escolares |
| `ibge_malha_br` | Malhas Territoriais Nacionais | Fronteiras municipais e estaduais |
| `ibge_malha_go` | Malhas Territoriais Goiás | Fronteiras municipais de Goiás |

### 🏥 Saúde (DATASUS/MS)

| ID | Dataset | Descrição |
|---|---|---|
| `datasus_sim_dores` | SIM – Óbitos por CID-10 | Mortalidade adulta por causa |
| `datasus_sim_doinf` | SIM – Óbitos Infantis | Mortalidade infantil |
| `datasus_pops` | Estimativas Populacionais | Base de denominadores para taxas |
| `sinasc` | SINASC – Nascidos Vivos | Escolaridade materna, condições de nascimento |

### 💰 Financeiro (Tesouro Nacional / FNDE)

| ID | Dataset | Descrição |
|---|---|---|
| `siope` | SIOPE – Orçamentos Públicos em Educação | Gasto/aluno, vinculação constitucional, FUNDEB |
| `tesouro_transparente` | Execução Orçamentária Federal – Educação | Função 12 / SIAFI |

### 🔍 Transparência e Controle

| ID | Dataset | Fonte |
|---|---|---|
| `portal_transparencia_federal` | Portal da Transparência Federal | CGU |
| `cgu_acordos_leniencia` | Acordos de Leniência e Sanções (CEIS/CNEP) | CGU |
| `tcu_acordaos` | Acórdãos e Controle Externo | TCU |
| `cnj_dados_judiciarios` | Justiça em Números | CNJ |
| `cnmp_dados_mp` | MP em Números | CNMP |
| `mpf_dados_abertos` | MPF – Dados Abertos Federais | MPF |

### 🧪 Ciência e Tecnologia

| ID | Dataset | Fonte |
|---|---|---|
| `cnpq_bolsas_fomentos` | Bolsas e Grupos de Pesquisa | CNPq/MCTI |
| `inpi_patentes` | Patentes e Propriedade Industrial | INPI/MDIC |
| `mcti_investimentos_ct` | Indicadores de C,T&I | MCTI |

### 🏙️ Prefeituras e Estados

| ID | Dataset | Fonte |
|---|---|---|
| `prefeitura_sp` | São Paulo – Dados Abertos | PMSP |
| `prefeitura_rio` | Rio de Janeiro – Dados Abertos | PCRJ |
| `prefeitura_goiania` | Goiânia – Dados Abertos | PMG |
| `goias_educacao` | Goiás – Educação (SEDUC-GO) | SEDUC-GO |
| `goias_saude` | Goiás – Saúde (SES-GO) | SES-GO |
| `goias_saneamento` | Goiás – Saneamento (AGR-GO) | AGR-GO |
| `snis_residuos` | SNIS – Resíduos Sólidos | SNIS/MCidades |

---

## Adicionando um novo dataset

Crie `catalog/<categoria>/<id>.yaml` e abra um Pull Request:

```yaml
id: meu_dataset
name: "Nome do Dataset"
source: "Órgão Responsável"
category: educacao
description: |
  Descrição com pelo menos 10 caracteres.
tags: [tag1, tag2]
license: "Dados Abertos"
url_type: pattern          # pattern | static_list | dynamic | ftp
file_format: zip
years:
  start: 2015
  end: 2024
url_pattern: "https://fonte.gov.br/dados_{year}.zip"
est_size_mb_per_year: 50
dest_folder: "orgao/meu_dataset"
checks:
  - type: file_exists
  - type: zip_valid
```

```bash
dados-br catalog validate   # valida antes de commitar
```

---

## Uso programático

```python
from dadosbr.registry import registry
from dadosbr.indicators import indicator_registry, IndicatorLevel
from dadosbr.downloader import DownloadConfig, download_urls
from pathlib import Path

# --- Catálogo de datasets ---
registry.load()
ds = registry.get("censo_escolar")
urls = ds.urls_for_years([2021, 2022, 2023])

config = DownloadConfig(output_dir=Path("dados"), dry_run=True)
summary = download_urls(urls, config)

# --- Indicadores e perguntas norteadoras ---
indicator_registry.load()

# Todos os indicadores de educação básica
basicos = indicator_registry.by_level(IndicatorLevel.BASICA)

# Perguntas norteadoras relacionadas ao Censo Escolar
perguntas = indicator_registry.questions_for_dataset("censo_escolar")
for ind_id, qs in perguntas.items():
    print(f"\n{ind_id}:")
    for q in qs:
        print(f"  → {q}")

# Informações completas do IDEB
ideb = indicator_registry.require("ideb")
print(ideb.citations)         # referências ABNT
print(ideb.research_questions)  # perguntas norteadoras
print(ideb.source_datasets)    # ['saeb', 'censo_escolar']

# Total de perguntas disponíveis
todas = indicator_registry.all_research_questions()
print(f"{len(todas)} perguntas norteadoras em {len(indicator_registry)} indicadores")
```

---

## Estrutura do projeto

```
dados-br/
├── dadosbr/                  # Pacote Python principal
│   ├── cli.py                # CLI Typer + Rich
│   ├── models.py             # Modelos Pydantic do catálogo
│   ├── registry.py           # Registry lazy de datasets
│   ├── indicators.py         # Registry de indicadores + perguntas norteadoras
│   ├── downloader.py         # Engine de download (httpx + FTP)
│   ├── extractor.py          # Extração de ZIPs
│   ├── checker.py            # Checagens de integridade
│   └── utils.py              # Utilitários
├── catalog/                  # Catálogo declarativo em YAML
│   ├── inep_mec/             # ENEM, Censo Escolar, SAEB, ...
│   ├── ibge/                 # PNADc, Censo Demográfico, PeNSE, Malhas
│   ├── datasus/              # SIM, SINASC, Populações
│   ├── financeiro/           # SIOPE, Tesouro Transparente
│   ├── transparencia/        # Portal da Transparência, CGU
│   ├── tribunais/            # TCU, CNJ
│   ├── mp/                   # CNMP, MPF
│   ├── ct/                   # CAPES, CNPq, INPI, MCTI
│   ├── prefeituras/          # SP, Rio, Goiânia
│   ├── goias/                # SEDUC-GO, SES-GO, AGR-GO
│   ├── educacao/             # UFRN
│   ├── snis/                 # Resíduos Sólidos
│   └── indicators/           # Indicadores com citações e perguntas norteadoras
│       ├── educacao_basica.yaml      # 15 indicadores INEP
│       ├── educacao_superior.yaml   # 4 indicadores INEP
│       ├── ibge_social.yaml         # 5 indicadores IBGE
│       ├── datasus_saude.yaml       # 4 indicadores DATASUS
│       ├── financeiro_educacao.yaml # 4 indicadores SIOPE/Tesouro
│       └── outros_datasets.yaml     # 6 indicadores transversais
├── tests/                    # Testes pytest
└── .github/workflows/        # CI (testes + lint) e Release (PyPI)
```

---

## Tecnologias (todas software livre)

[Typer](https://typer.tiangolo.com/) · [Rich](https://rich.readthedocs.io/) · [Pydantic v2](https://docs.pydantic.dev/) · [PyYAML](https://pyyaml.org/) · [httpx](https://www.python-httpx.org/) · [pandas](https://pandas.pydata.org/) · [PyArrow](https://arrow.apache.org/docs/python/) · [DuckDB](https://duckdb.org/) · [pytest](https://pytest.org/)

---

## Contribuindo

Veja [CONTRIBUTING.md](CONTRIBUTING.md). A forma mais simples de contribuir é adicionar um dataset — basta criar um arquivo YAML e abrir um Pull Request.

---

## Autor

**Carlos Artur Guimarães**
Pesquisador e gestor público com foco em dados educacionais e governança digital.
Natal, RN.

- GitHub: [@tucaguimaraes](https://github.com/tucaguimaraes)
- E-mail: carlostucaguimaraes@gmail.com

---

## Licença

[Apache License 2.0](LICENSE) — você pode usar, modificar e redistribuir livremente, inclusive para fins comerciais, desde que mantenha a atribuição.

---

*dados-br é um projeto independente, não afiliado ao governo brasileiro. Os dados são públicos e disponibilizados pelos órgãos governamentais em seus respectivos portais.*
