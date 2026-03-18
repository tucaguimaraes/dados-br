# Publicando o dados-br no GitHub

Guia completo do zero para hospedar o projeto em **github.com/tucaguimaraes/dados-br**.

---

## Passo 1 — Criar o repositório no GitHub

1. Acesse **github.com/new**
2. Preencha:
   - **Repository name:** `dados-br`
   - **Description:** `Ferramenta open source para catalogar, baixar e analisar dados públicos brasileiros`
   - **Visibility:** ✅ Public
   - **NÃO marque** nenhuma opção de inicialização (README, .gitignore, License) — o projeto já tem tudo isso
3. Clique em **Create repository**

---

## Passo 2 — Criar o Personal Access Token

O GitHub não aceita senha comum para operações Git. É obrigatório usar um token.

1. Acesse **github.com → sua foto (canto superior direito) → Settings**
2. No menu esquerdo, role até o final: **Developer settings**
3. **Personal access tokens → Tokens (classic)**
4. **Generate new token → Generate new token (classic)**
5. Preencha:
   - **Note:** `dados-br`
   - **Expiration:** 90 days
   - **Scopes:** marque ✅ `repo` (primeira opção da lista)
6. Clique em **Generate token**
7. **Copie o token agora** — ele começa com `ghp_` e aparece uma única vez

> ⚠️ Guarde o token em local seguro. Nunca o compartilhe nem o publique.

---

## Passo 3 — Configurar o git local

No terminal, dentro da pasta `dados-br`:

```bash
# Verificar se já existe algum remote configurado
git remote -v
```

Se aparecer qualquer remote listado, remova:

```bash
git remote remove origin
```

Agora adicione o remote correto:

```bash
git remote add origin https://github.com/tucaguimaraes/dados-br.git
```

Confirme que ficou certo:

```bash
git remote -v
```

Saída esperada:
```
origin  https://github.com/tucaguimaraes/dados-br.git (fetch)
origin  https://github.com/tucaguimaraes/dados-br.git (push)
```

---

## Passo 4 — Fazer o push

```bash
git push -u origin main
```

O terminal vai pedir credenciais:

```
Username: tucaguimaraes
Password: ghp_SEU_TOKEN_AQUI   ← cole o token, não a senha do GitHub
```

> **Dica Mac:** depois do primeiro push bem-sucedido, rode:
> ```bash
> git config --global credential.helper osxkeychain
> ```
> O Mac salva o token no Keychain e os próximos pushes não pedem mais credenciais.

---

## Passo 5 — Verificar no GitHub

Acesse **github.com/tucaguimaraes/dados-br** — todos os arquivos devem aparecer.

Em seguida, clique em **Actions** para acompanhar o CI rodando automaticamente.
Se tudo estiver verde, o projeto está publicado e funcional.

---

## Passo 6 — Completar o perfil do repositório

Em **github.com/tucaguimaraes/dados-br**, clique na engrenagem ao lado de "About":

- **Description:** `Ferramenta open source para catalogar, baixar e analisar dados públicos brasileiros`
- **Topics:** adicione um a um:
  `dados-abertos` · `brazil` · `python` · `open-data` · `education` · `government` · `cli` · `research`

---

## Passo 7 — Criar a release v0.1.0

```bash
# Dentro da pasta dados-br, criar a tag
git tag -a v0.1.0 -m "v0.1.0 — MVP: 35 datasets, 38 indicadores, CLI completa"

# Enviar a tag para o GitHub
git push origin v0.1.0
```

No GitHub:

1. Acesse **github.com/tucaguimaraes/dados-br/releases/new**
2. **Choose a tag:** selecione `v0.1.0`
3. **Release title:** `v0.1.0 — Lançamento Inicial`
4. Cole no campo de descrição:

```markdown
## dados-br v0.1.0

Primeiro lançamento público — ferramenta open source para catalogar,
baixar, validar e analisar dados públicos brasileiros.

### O que está incluído

- 35 datasets de fontes abertas (INEP, IBGE, DATASUS, Tesouro, CGU, TCU...)
- 38 indicadores com citações ABNT e perguntas norteadoras para pesquisa
- CLI completa: `dados-br list`, `download`, `check`, `catalog`, `indicators`
- Download HTTP + FTP com retry, progress bar e estimativa de tamanho
- Validação automática de integridade dos arquivos baixados
- API Python programática — Apache 2.0

### Instalação

pip install dados-br
```

5. Clique em **Publish release**

---

## Passo 8 — Publicar no PyPI (opcional)

O workflow `.github/workflows/release.yml` já está configurado.
Toda release no GitHub publica automaticamente no PyPI.

### Criar conta e token no PyPI

1. Crie conta em **pypi.org/account/register** (se não tiver)
2. **Account Settings → API tokens → Add API token**
   - Nome: `dados-br-github`
   - Scope: `Entire account`
3. Copie o token gerado (começa com `pypi-...`)

### Adicionar o secret no GitHub

1. **github.com/tucaguimaraes/dados-br → Settings → Secrets and variables → Actions**
2. **New repository secret**
   - Name: `PYPI_API_TOKEN`
   - Secret: cole o token do PyPI
3. Clique em **Add secret**

A próxima release publicará automaticamente no PyPI.
Qualquer pessoa poderá instalar com `pip install dados-br`.

---

## Resumo dos comandos (do zero ao push)

```bash
# Na pasta dados-br, executar em sequência:

git remote remove origin
git remote add origin https://github.com/tucaguimaraes/dados-br.git
git push -u origin main

# Após o push, salvar credenciais no Mac:
git config --global credential.helper osxkeychain

# Criar e publicar a tag da versão:
git tag -a v0.1.0 -m "v0.1.0 — MVP: 35 datasets, 38 indicadores, CLI completa"
git push origin v0.1.0
```

---

## Próximas atualizações — fluxo de trabalho

```bash
# Criar branch para cada nova feature ou correção
git checkout -b feat/nome-da-feature

# Fazer as alterações e commitar
git add .
git commit -m "feat: descrição do que foi feito"
git push origin feat/nome-da-feature

# Abrir Pull Request no GitHub → revisar → mesclar na main
```

---

*Repositório: github.com/tucaguimaraes/dados-br*
