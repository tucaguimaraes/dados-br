"""
Verificação rápida de instalação do dados-br.
Rode com: python verificar_instalacao.py

Não precisa de pytest. Testa imports, catálogo, indicadores e CLI.
"""

import sys
import subprocess

VERDE = "\033[92m"
VERMELHO = "\033[91m"
AMARELO = "\033[93m"
RESET = "\033[0m"
NEGRITO = "\033[1m"

passou = []
falhou = []


def ok(msg):
    passou.append(msg)
    print(f"  {VERDE}✓{RESET} {msg}")


def erro(msg, detalhe=""):
    falhou.append(msg)
    print(f"  {VERMELHO}✗{RESET} {msg}")
    if detalhe:
        print(f"    {AMARELO}→ {detalhe}{RESET}")


def secao(titulo):
    print(f"\n{NEGRITO}{titulo}{RESET}")
    print("─" * 50)


# ──────────────────────────────────────────────────
# 1. Imports
# ──────────────────────────────────────────────────
secao("1. Imports")

try:
    import dadosbr
    ok(f"import dadosbr  (versão {dadosbr.__version__})")
except ImportError as e:
    erro("import dadosbr", str(e))

try:
    from dadosbr.registry import registry
    ok("from dadosbr.registry import registry")
except ImportError as e:
    erro("from dadosbr.registry import registry", str(e))

try:
    from dadosbr.indicators import indicator_registry
    ok("from dadosbr.indicators import indicator_registry")
except ImportError as e:
    erro("from dadosbr.indicators import indicator_registry", str(e))

try:
    from dadosbr.cli import app
    ok("from dadosbr.cli import app")
except ImportError as e:
    erro("from dadosbr.cli import app", str(e))


# ──────────────────────────────────────────────────
# 2. Catálogo de datasets
# ──────────────────────────────────────────────────
secao("2. Catálogo de datasets")

try:
    from dadosbr.registry import registry
    registry.load()
    total = len(registry)
    if total >= 35:
        ok(f"Catálogo carregado: {total} datasets")
    else:
        erro(f"Catálogo com poucos datasets: {total} (esperado ≥ 35)")
except Exception as e:
    erro("Falha ao carregar catálogo", str(e))

try:
    ds = registry.get("enem")
    if ds:
        ok(f"Dataset 'enem' encontrado: {ds.name}")
    else:
        erro("Dataset 'enem' não encontrado no catálogo")
except Exception as e:
    erro("Erro ao buscar dataset 'enem'", str(e))

try:
    cats = registry.categories()
    if "educacao" in cats:
        ok(f"Categorias disponíveis: {', '.join(cats)}")
    else:
        erro("Categoria 'educacao' não encontrada", str(cats))
except Exception as e:
    erro("Erro ao listar categorias", str(e))

try:
    errors = registry.validate_all()
    if not errors:
        ok("Validação do catálogo: sem erros")
    else:
        erro(f"Catálogo tem {len(errors)} problema(s)", str(list(errors.keys())[:3]))
except Exception as e:
    erro("Erro na validação do catálogo", str(e))


# ──────────────────────────────────────────────────
# 3. Módulo de indicadores
# ──────────────────────────────────────────────────
secao("3. Indicadores")

try:
    from dadosbr.indicators import indicator_registry
    indicator_registry.load()
    total_ind = len(indicator_registry)
    if total_ind >= 38:
        ok(f"Indicadores carregados: {total_ind}")
    else:
        erro(f"Poucos indicadores: {total_ind} (esperado ≥ 38)")
except Exception as e:
    erro("Falha ao carregar indicadores", str(e))

try:
    ind = indicator_registry.get("ideb")
    if ind:
        ok(f"Indicador 'ideb' encontrado: {ind.name}")
    else:
        erro("Indicador 'ideb' não encontrado")
except Exception as e:
    erro("Erro ao buscar indicador 'ideb'", str(e))

try:
    questions = indicator_registry.all_research_questions()
    if len(questions) >= 155:
        ok(f"Perguntas norteadoras: {len(questions)}")
    else:
        erro(f"Poucas perguntas: {len(questions)} (esperado ≥ 155)")
except Exception as e:
    erro("Erro ao listar perguntas norteadoras", str(e))

try:
    erros_ind = indicator_registry.validate()
    if not erros_ind:
        ok("Validação dos indicadores: sem erros")
    else:
        erro(f"Indicadores com {len(erros_ind)} problema(s)", str(erros_ind[:2]))
except Exception as e:
    erro("Erro na validação dos indicadores", str(e))


# ──────────────────────────────────────────────────
# 4. Cobertura datasets × indicadores
# ──────────────────────────────────────────────────
secao("4. Cobertura datasets × indicadores")

try:
    todos_datasets = {d.id for d in registry.all()}
    referenciados = set()
    for ind in indicator_registry.all():
        for ds_id in ind.source_datasets:
            referenciados.add(ds_id)

    sem_indicador = todos_datasets - referenciados
    if not sem_indicador:
        ok(f"100% dos datasets têm indicador ({len(todos_datasets)}/{len(todos_datasets)})")
    else:
        erro(f"{len(sem_indicador)} dataset(s) sem indicador", str(sorted(sem_indicador)))
except Exception as e:
    erro("Erro na verificação de cobertura", str(e))


# ──────────────────────────────────────────────────
# 5. CLI
# ──────────────────────────────────────────────────
secao("5. CLI (dados-br)")

try:
    result = subprocess.run(
        ["dados-br", "--help"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0 and "download" in result.stdout.lower():
        ok("dados-br --help  (comando disponível)")
    else:
        erro("dados-br --help retornou erro", result.stderr[:100])
except FileNotFoundError:
    erro("Comando 'dados-br' não encontrado", "Rode: pip install -e .")
except Exception as e:
    erro("Erro ao executar CLI", str(e))

try:
    result = subprocess.run(
        ["dados-br", "list"],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        ok("dados-br list  (listagem OK)")
    else:
        erro("dados-br list retornou erro", result.stderr[:100])
except Exception as e:
    erro("Erro ao executar 'dados-br list'", str(e))

try:
    result = subprocess.run(
        ["dados-br", "indicators", "list"],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        ok("dados-br indicators list  (indicadores OK)")
    else:
        erro("dados-br indicators list retornou erro", result.stderr[:100])
except Exception as e:
    erro("Erro ao executar 'dados-br indicators list'", str(e))

try:
    result = subprocess.run(
        ["dados-br", "indicators", "info", "ideb"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0 and "ideb" in result.stdout.lower():
        ok("dados-br indicators info ideb  (detalhe OK)")
    else:
        erro("dados-br indicators info ideb retornou erro", result.stderr[:100])
except Exception as e:
    erro("Erro ao executar 'dados-br indicators info ideb'", str(e))


# ──────────────────────────────────────────────────
# Resultado final
# ──────────────────────────────────────────────────
total = len(passou) + len(falhou)
print(f"\n{'═' * 50}")
print(f"{NEGRITO}Resultado: {len(passou)}/{total} verificações passaram{RESET}")

if falhou:
    print(f"\n{VERMELHO}Falhas:{RESET}")
    for f in falhou:
        print(f"  • {f}")
    print(f"\n{AMARELO}Dica: rode 'pip install -e .' dentro da pasta dados-br{RESET}")
    sys.exit(1)
else:
    print(f"\n{VERDE}{NEGRITO}✓ Instalação verificada com sucesso!{RESET}")
    print(f"\nPróximos passos:")
    print(f"  dados-br list")
    print(f"  dados-br indicators info ideb")
    print(f"  dados-br download censo_escolar --years 2023 --dry-run")
    sys.exit(0)
