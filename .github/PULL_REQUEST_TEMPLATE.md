## Descrição

<!-- Descreva as mudanças deste PR em 1-3 frases. -->

## Tipo de mudança

- [ ] 🐛 Correção de bug
- [ ] ✨ Nova funcionalidade
- [ ] 📦 Novo dataset no catálogo
- [ ] 🔧 Refatoração (sem mudança de comportamento)
- [ ] 📝 Documentação
- [ ] 🔒 Segurança
- [ ] ⚙️ CI/CD / configuração

## Dataset (se aplicável)

- **ID do dataset:** <!-- ex: censo_superior -->
- **Fonte:** <!-- ex: INEP/MEC -->
- **Anos cobertos:** <!-- ex: 2010–2023 -->
- **Validado com dry-run:** <!-- sim / não -->

## Checklist

- [ ] Os testes existentes passam (`pytest`)
- [ ] Adicionei testes para as novas funcionalidades (se aplicável)
- [ ] Rodei `ruff check .` sem erros
- [ ] Atualizei o `CHANGELOG.md` (seção `[Unreleased]`)
- [ ] Atualizei a documentação afetada (README, docstrings)
- [ ] Para novo dataset: testei `dados-br download <id> --dry-run`

## Evidência de teste

<!-- Cole a saída do comando ou o resultado do pytest -->

```
$ pytest tests/ -v
...
```

## Issues relacionadas

<!-- Closes #xxx -->
