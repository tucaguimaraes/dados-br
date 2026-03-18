#!/usr/bin/env bash
# =============================================================================
# download_amostras.sh — Download de bases de dados para pesquisa (~10 GB)
#
# Seleciona os principais datasets educacionais e sociais brasileiros
# organizados por tema, totalizando aproximadamente 10 GB.
#
# Uso:
#   chmod +x download_amostras.sh
#   ./download_amostras.sh
#
# Para simular sem baixar nada (recomendado antes de rodar):
#   DRY_RUN=1 ./download_amostras.sh
#
# Para escolher onde salvar (padrão: ~/dados-br/):
#   DADOS_DIR=~/Documentos/pesquisa ./download_amostras.sh
# =============================================================================

set -euo pipefail

VERDE="\033[92m"
AMARELO="\033[93m"
AZUL="\033[94m"
NEGRITO="\033[1m"
RESET="\033[0m"

DRY_RUN="${DRY_RUN:-0}"
DADOS_DIR="${DADOS_DIR:-$HOME/dados-br}"
DRY_FLAG=""
if [ "$DRY_RUN" = "1" ]; then
  DRY_FLAG="--dry-run"
  echo -e "${AMARELO}${NEGRITO}⚠ Modo DRY RUN — nenhum arquivo será baixado${RESET}\n"
fi

echo -e "${NEGRITO}dados-br — Download de Amostras (~10 GB)${RESET}"
echo -e "Destino: ${AZUL}${DADOS_DIR}${RESET}\n"
echo "============================================================"

download() {
  local titulo="$1"
  local dataset="$2"
  shift 2
  echo -e "\n${NEGRITO}${AZUL}▶ ${titulo}${RESET}"
  dados-br download "$dataset" --data-dir "$DADOS_DIR" $DRY_FLAG "$@"
}

# ─────────────────────────────────────────────────────────────────────────────
# GRUPO 1 — INEP / Avaliação e Fluxo Escolar          ~5.3 GB
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${NEGRITO}GRUPO 1 — INEP / Avaliação e Fluxo Escolar${RESET} (est. ~5.3 GB)"
echo "------------------------------------------------------------"

# ENEM 2018–2023  →  6 × 300 MB ≈ 1.8 GB
download "ENEM — Exame Nacional do Ensino Médio (2018–2023)" \
  enem --years 2018-2023

# Censo Escolar 2018–2023  →  6 × 250 MB ≈ 1.5 GB
download "Censo Escolar (2018–2023)" \
  censo_escolar --years 2018-2023

# SAEB 2015–2023  →  5 edições × 400 MB ≈ 2.0 GB  (bienal: 2015,2017,2019,2021,2023)
download "SAEB — Sistema de Avaliação da Educação Básica (2015–2023)" \
  saeb --years 2015-2023

# ─────────────────────────────────────────────────────────────────────────────
# GRUPO 2 — INEP / Educação Superior e Indicadores    ~1.5 GB
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${NEGRITO}GRUPO 2 — INEP / Educação Superior e Indicadores${RESET} (est. ~1.5 GB)"
echo "------------------------------------------------------------"

# Censo da Educação Superior 2018–2023  →  6 × 200 MB ≈ 1.2 GB
download "Censo da Educação Superior (2018–2023)" \
  censo_superior --years 2018-2023

# ENCCEJA 2017–2023  →  ~4 edições × 80 MB ≈ 320 MB
download "ENCCEJA (2017–2023)" \
  encceja --years 2017-2023

# Distorção Idade-Série 2016–2024  →  9 × 5 MB ≈ 45 MB
download "Distorção Idade-Série — INEP (2016–2024)" \
  inep_tdi --years 2016-2024

# ─────────────────────────────────────────────────────────────────────────────
# GRUPO 3 — Financiamento da Educação                 ~1.1 GB
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${NEGRITO}GRUPO 3 — Financiamento da Educação${RESET} (est. ~1.1 GB)"
echo "------------------------------------------------------------"

# SIOPE — Finanças da Educação  ≈ 430 MB
download "SIOPE — Sistema de Informações sobre Orçamentos Públicos em Educação" \
  siope

# Tesouro Transparente  ≈ 95 MB
download "Tesouro Transparente — Execução Orçamentária Federal" \
  tesouro_transparente

# ─────────────────────────────────────────────────────────────────────────────
# GRUPO 4 — IBGE / Dados Sociodemográficos            ~770 MB
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${NEGRITO}GRUPO 4 — IBGE / Dados Sociodemográficos${RESET} (est. ~770 MB)"
echo "------------------------------------------------------------"

# Censo Demográfico 2022  ≈ 660 MB
download "Censo Demográfico IBGE 2022" \
  censo_demografico

# PeNSE — Pesquisa Nacional de Saúde do Escolar  ≈ 55 MB
download "PeNSE — Pesquisa Nacional de Saúde do Escolar" \
  pense

# Malha Municipal Brasil  ≈ 58 MB
download "Malha Municipal Brasileira — IBGE" \
  ibge_malha_br

# ─────────────────────────────────────────────────────────────────────────────
# GRUPO 5 — Goiás (dados estaduais de referência)     ~40 MB
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${NEGRITO}GRUPO 5 — Goiás / Dados Estaduais de Referência${RESET} (est. ~40 MB)"
echo "------------------------------------------------------------"

download "Educação Básica — Goiás" \
  goias_educacao

download "Saúde — Goiás" \
  goias_saude

download "Saneamento — Goiás" \
  goias_saneamento

download "Malha Municipal — Goiás" \
  ibge_malha_go

# ─────────────────────────────────────────────────────────────────────────────
# Resumo
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
if [ "$DRY_RUN" = "1" ]; then
  echo -e "${AMARELO}Simulação concluída. Nenhum arquivo foi baixado.${RESET}"
  echo -e "Para baixar de verdade, execute: ${NEGRITO}./download_amostras.sh${RESET}"
else
  echo -e "${VERDE}${NEGRITO}Download concluído!${RESET}"
  echo -e "Arquivos salvos em: ${AZUL}${DADOS_DIR}${RESET}"
  echo ""
  echo "Para verificar os downloads, rode:"
  echo "  dados-br check enem --data-dir $DADOS_DIR"
  echo "  dados-br check censo_escolar --data-dir $DADOS_DIR"
fi
echo ""
echo "Tamanho estimado por grupo:"
echo "  Grupo 1 — INEP Avaliação:          ~5.3 GB"
echo "  Grupo 2 — Educação Superior:       ~1.5 GB"
echo "  Grupo 3 — Financiamento:           ~1.1 GB"
echo "  Grupo 4 — IBGE Sociodemográfico:   ~0.8 GB"
echo "  Grupo 5 — Goiás:                   ~0.1 GB"
echo "  ─────────────────────────────────────────"
echo "  TOTAL estimado:                    ~8.8 GB"
echo ""
echo "Para explorar os indicadores relacionados:"
echo "  dados-br indicators for-dataset enem"
echo "  dados-br indicators for-dataset censo_escolar"
echo "  dados-br indicators list --level basica"
