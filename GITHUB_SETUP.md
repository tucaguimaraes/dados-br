# Como publicar o dados-br no GitHub

Guia passo a passo para hospedar e publicar o projeto.

---

## Pré-requisitos

- Conta no GitHub criada e repositório `dados-br` criado em **github.com/SEU_USUARIO/dados-br**
- Git instalado (`git --version` para verificar)
- Projeto com `git init` e primeiro commit já feitos

---

## 1. Configurar o remote

```bash
# Remover qualquer remote incorreto existente
git remote remove origin

# Adicionar o remote correto (com https://)
git remote add origin https://github.com/SEU_USUARIO/dados-br.git

# Verificar
git remote -v
```

A saída esperada:
```
origin  https://github.com/SEU_USUARIO/dados-br.git (fetch)
origin  https://github.com/SEU_USUARIO/dados-br.git (push)
```

---

## 2. Autenticação — Personal Access Token (PAT)

O GitHub não aceita senha comum para operações Git. É necessário um **Personal Access Token**.

### Criar o token

1. Acesse: **github.com → foto do perfil → Settings**
2. No menu esquerdo (final da página): **Developer settings**
3. **Personal access tokens → Tokens (classic)**
4. **Generate new token → Generate new token (classic)**
5. Preencha:
   - **Note:** `dados-br-push` (qualquer nome descritivo)
   - **Expiration:** 90 days (recomendado) ou No expiration
   - **Scopes:** marque ✅ `repo`
6. Clique em **Generate token**
7. **Copie o token agora** — começa com `ghp_...` e só aparece uma vez

> ⚠️ Nunca compartilhe ou publique o token. Trate-o como uma senha.

### Fazer o push

```bash
git push -u origin main
```

Quando pedir credenciais:
- **Username:** seu usuário do GitHub
- **Password:** cole o token `ghp_...`

### Salvar para não repetir

```bash
# Mac — salva no Keychain automaticamente
git config --global credential.helper osxkeychain
```

Após configurar, o próximo push já não pedirá credenciais.

---

## 3. Criar a release v0.1.0

```bash
# Criar tag anotada
git tag -a v0.1.0 -m "v0.1.0 — MVP: 35 datasets, 38 indicadores, CLI completa"

# Enviar a tag para o GitHub
git push origin v0.1.0
```

No GitHub:

1. Acesse **github.com/SEU_USUARIO/dados-br → Releases → Create a new release**
2. **Choose a tag:** selecione `v0.1.0`
3. **Title:** `v0.1.0 — Lançamento Inicial`
4. **Description:**

```
## dados-br v0.1.0

Primeiro lançamento público — ferramenta open source para catalogar,
baixar, validar e analisar dados públicos brasileiros.

### Incluído nesta versão

- 35 datasets de fontes abertas (INEP, IBGE, DATASUS, Tesouro, CGU, TCU...)
- 38 indicadores com citações ABNT e perguntas norteadoras para pesquisa
- CLI: `dados-br list`, `download`, `check`, `catalog`, `indicators`
- Download HTTP + FTP com retry, progress bar e estimativa de tamanho
- API Python programática (Apache 2.0)

### Instalação

pip install dados-br
```

5. Clique em **Publish release**

---

## 4. Publicar no PyPI (automático via GitHub Actions)

O projeto já inclui o workflow `.github/workflows/release.yml`.
Toda release criada no GitHub publica automaticamente no PyPI.

### Configurar o secret

1. Crie uma conta em **pypi.org** (se ainda não tiver)
2. **Account Settings → API tokens → Add API token**
   - Nome: `dados-br-github`, Scope: `Entire account`
   - Copie o token gerado (começa com `pypi-...`)
3. No GitHub: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `PYPI_API_TOKEN`
   - Secret: cole o token do PyPI

A partir daí, ao criar qualquer nova release, o pacote é publicado automaticamente.
Qualquer pessoa poderá instalar com `pip install dados-br`.

---

## 5. Configurar o repositório no GitHub

Em **github.com/SEU_USUARIO/dados-br**, clique na engrenagem ao lado de "About":

- **Description:** `Ferramenta open source para catalogar, baixar e analisar dados públicos brasileiros`
- **Topics:** `dados-abertos` `brazil` `python` `open-data` `education` `government` `cli` `research`

---

## 6. Proteger o branch main

1. **Settings → Branches → Add branch protection rule**
2. **Branch name pattern:** `main`
3. Marque:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass → selecione `CI`
4. Clique em **Create**

---

## 7. Fluxo para novas atualizações

```bash
# Criar branch para cada nova feature
git checkout -b feat/nome-da-feature

# Fazer as alterações...
git add .
git commit -m "feat: descrição do que foi feito"
git push origin feat/nome-da-feature

# Abrir Pull Request no GitHub para revisão antes de mesclar na main
```

---

## Próximos passos após o primeiro push

1. ✅ Verificar CI em: **github.com/SEU_USUARIO/dados-br/actions**
2. 📦 Configurar `PYPI_API_TOKEN` e criar a release v0.1.0
3. 📢 Publicar o post no LinkedIn (veja `LINKEDIN_POST.md`)
4. 🏷️ Adicionar topics ao repositório
