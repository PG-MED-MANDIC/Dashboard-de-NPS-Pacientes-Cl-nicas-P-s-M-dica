# Progresso — Dashboard de NPS (SLMandic)

Documento de continuidade: estado atual do projeto, decisões tomadas e o que falta. Última atualização: 2026-09-15.

## Próximo passo imediato (retomar daqui)

**Os 4 dashboards deste workspace estão atualizados, publicados no GitHub Pages e comparados com a
versão de referência (conta antiga `TCM-18`, ainda mantida em paralelo por outra pessoa). Só faltam 2
decisões/verificações externas (não são bugs de código) -- ver "Pendências" no fim deste arquivo, e o
resumo em `COMPARACAO_TCM18.txt` (raiz, não versionado, feito pra validação em 16/09/2026).**

### Mudança de estrutura importante (15/09/2026): workspace consolidado

Esta pasta (`NPS-PACIENTE`) deixou de ser só o repositório do dashboard de NPS de paciente -- agora é a
**pasta-mãe de 4 repositórios independentes**, cada um com seu próprio `.git`/remoto, vivendo juntos só
por conveniência (pra atualizar tudo num lugar só, ver `CONTEXTO-GITHUB.md` na raiz, não versionado):

1. **raiz desta pasta** (`index.html`/`script.js`/`pipeline/`) -- este dashboard (NPS de paciente).
2. **`agendas-pac-real/`** -- Dashboard Triagem (ConsultaJá).
3. **`agendas_pgmed/`** -- Acompanhamento Semanal de Práticas (planilha do SharePoint).
4. **`csat/`** -- CSAT Pós Med / dataset "CSAT por item" (Indecx, pesquisa diferente da de paciente).

O `.gitignore` da raiz ignora as 3 subpastas (cada uma é commitada/publicada separadamente, `cd` até ela
antes de `git add`/`commit`/`push`) e os arquivos de nota local (`CONTEXTO-GITHUB.md`,
`COMPARACAO_TCM18.txt`).

**Conta do GitHub também mudou**: migrado de `TCM-18` (antiga, ainda mantida por outra pessoa em
paralelo -- ver seção de comparação abaixo) para `PG-MED-MANDIC` (atual, onde tudo daqui pra frente deve
ser publicado). Os 4 repositórios estão com **GitHub Pages ativado** (Settings → Pages → branch `main` →
`/root`, ativado em 15/09/2026):

- `https://pg-med-mandic.github.io/Dashboard-de-NPS-Pacientes-Cl-nicas-P-s-M-dica/`
- `https://pg-med-mandic.github.io/agendas-pac-real/`
- `https://pg-med-mandic.github.io/csat/`
- `https://pg-med-mandic.github.io/agendas_pgmed/`

### O que já funciona (não precisa mexer de novo)

- **Indecx (NPS de paciente) resolvido de ponta a ponta.** `indecx_client.py` replica o fluxo de automação de
  `ouvidoria-csat/motor` (login → solicitar exportação → polling → download). `pipeline/.env` preenchido e
  testado. Validado contra export manual do Indecx duas vezes (03/09 e 04/09) via `comparar_planilhas.py`
  (célula a célula, sem expor dado sensível) -- sempre 0 diferenças nas respostas em comum.
- **CONSULTAJA_END_DATE agora é automático** (`pipeline/config.py: default_consultaja_end_date()`): sempre
  fim do mês, 2 meses à frente de hoje, recalculado a cada execução -- não precisa mais editar o `.env`
  manualmente quando o mês vira.
- **Comando único pra atualizar tudo**: `python pipeline/atualizar_tudo.py` roda as duas fontes (ConsultaJá →
  `ATENDIMENTOS`, Indecx → `RECORDS`/`WEEKLY`) e grava `script.js`. Não faz commit/push (continua manual, de
  propósito). `Atualizar Dashboard.bat` (raiz) chama esse mesmo script -- duplo clique faz tudo.
- **Reaproveitamento da planilha da ConsultaJá entre repositórios (15/09/2026)**: como `agendas-pac-real`
  agora vive na mesma pasta e usa a mesma conta/token, `pipeline/atualizar_tudo.py` (dos dois lados) checa
  se a planilha do dia (`dados-fonte/Base_Consulta_Ja<AAMMDD>.xlsx`, pasta compartilhada) já existe antes de
  chamar a API -- quem rodar primeiro no dia baixa, o outro reaproveita. Elimina download duplicado.
- **Bug do Engajamento revertido (08/09/2026, ver commit `5ad0d9b`)**: atendimento volta a contar
  `Compareceu` **ou** `Atendido` (não só `Compareceu`) -- ver "Decisões de negócio confirmadas".
- **Dados atuais em `script.js`** (gravados em 15/09/2026): 156 respostas de NPS; `ATENDIMENTOS` com 765
  combinações dia+unidade. Um CPF digitado por engano num comentário (unidade QUINTAL SLM - BRASÍLIA,
  06/08/2026) foi removido automaticamente pelo `sanitize.py` -- confirmado que só `[removido]` entrou no
  arquivo (planilha bruta original só existe local, em `dados-fonte/`, nunca versionada).
- **29+ respostas de NPS vêm com `unidade` em branco** (dado assim na origem, não é bug do pipeline) --
  entram no total geral ("Tudo"/sem filtro), somem se filtrar por unidade específica. Causa não confirmada.

### Repositórios irmãos (15/09/2026) -- pipelines novos

- **`agendas-pac-real`**: pipeline Python completo (`pipeline/atualizar_tudo.py`), mesmo padrão da raiz --
  busca ConsultaJá (reaproveitando a planilha da raiz quando possível), gera `RAW`/`RAWD`/`RAWH`/`DAYCNT`
  em `index.html`. Testado contra dado real: **100% das combinações turma+data batem com a versão de
  referência (TCM-18)**, exceto 1 turma que nosso token não enxerga -- ver "Pendências".
- **`csat`**: pipeline Python completo -- busca a pesquisa "CSAT por item" no Indecx (mesma conta da raiz,
  `groupId`/`actionId`/`metric` próprios) e regrava `DATA_GERAL`/`DATA_ITENS`/`DATA_FEEDBACK`/`DATA_TURMAS`.
  **Não cobre** o dataset "NPS Pós-Médica" (`DATA_NPS`/`DATA_FEEDBACK_FULL`, pesquisa Indecx ainda não
  identificada) -- esse continua sendo atualizado manualmente, fora do pipeline. Corrigidos 2 bugs reais
  (formula dos 6 itens de nota e fallback de coluna singular/plural) comparando com a referência -- ver
  `csat/pipeline/README.md` > "Fórmula dos itens". Resultado: **0 diferenças em todos os campos, nas 2193
  respostas em comum** com a versão de referência.
- **`agendas_pgmed`**: pipeline Python completo -- processa `checklist-captacao.xlsx` (baixado manualmente
  do SharePoint, ver `agendas_pgmed/pipeline/README.md`) e regrava `RAW` em `index.html`. Corrigidos 2 bugs
  reais: colunas renomeadas na planilha a partir de Set./2026 que o botão de upload manual não reconhecia,
  e um erro de digitação no cabeçalho da aba de Maio. Resultado: **as mesmas 1213 combinações turma+data em
  ambos os lados**, valores de capacidade idênticos -- só "agendamentos" varia (esperado, datas futuras
  recebendo novas matrículas).

### Comparação com a conta antiga (TCM-18) -- achados de 15/09/2026

A conta antiga (`TCM-18`) continua sendo atualizada por outra pessoa em paralelo à migração (`csat` em
15/09, `agendas_pgmed` e `agendas-pac-real` em 14/09 -- todos **depois** da migração pra `PG-MED-MANDIC`
em 11/09). Comparei dado a dado com nossos 3 repositórios equivalentes (ver `COMPARACAO_TCM18.txt`, não
versionado, escrito em linguagem simples pra validação):

- **`csat`**: corrigido, bate 100% agora (ver acima).
- **`agendas_pgmed`**: a versão de referência ganhou uma aba nova, "💰 Turmas Pagas" (simulação de receita
  de práticas extracurriculares pagas), alimentada por uma marcação manual (turma por turma) que não vem
  de nenhuma planilha -- não replicado aqui ainda. Precisa: (a) a lista de quais turmas são pagas, (b)
  construir a aba (desenvolvimento novo, não é ajuste de pipeline).
  **Nota**: essa aba não muda o texto de "Última atualização" do card do dashboard.
- **`agendas-pac-real`**: falta 1 turma ("Dermatologia Cirúrgica" T2, São Paulo) que existe na versão de
  referência mas não aparece nem na nossa planilha bruta da ConsultaJá -- é limitação de escopo/permissão
  do nosso token, não bug de transformação (confirmado: 59 de 60 combinações curso+turma batem).

## Estrutura do projeto

```
NPS-PACIENTE/                (pasta-mãe do workspace -- ver "Mudança de estrutura" acima)
  index.html          estrutura da página (NPS de paciente)
  style.css            tema navy/gold, claro/escuro
  script.js            dados embutidos (RECORDS/WEEKLY/ATENDIMENTOS) + toda a lógica de gráficos/filtros
  README.md            visão geral do dashboard + fluxo de atualização/publicação
  .gitignore            raiz do projeto -- protege .env, dado bruto, .venv, log local, e as 3 subpastas
                        de repositórios irmãos (ver abaixo)
  CONTEXTO-GITHUB.md   nota de workspace multi-repositório (não versionado -- só referência local)
  COMPARACAO_TCM18.txt nota de comparação com a conta antiga (não versionado -- validação de 16/09/2026)
  Atualizar Dashboard.bat   atalho local: roda atualizar_tudo.py (as duas fontes) e mostra o resumo
  COMO_ATUALIZAR.txt   passo a passo de atualização/publicação pro usuário rodar sozinho

  dados-fonte/          planilhas brutas (gitignored -- nunca versionar/hospedar), COMPARTILHADA com
                        agendas-pac-real/ (mesma conta ConsultaJá) e agendas_pgmed/ (planilha do SharePoint)

  pipeline/             scripts Python que regeneram os dados de script.js
    main.py                  RECORDS/WEEKLY a partir de export do Indecx (planilha em mãos ou baixada via API)
    update_attendance.py     ATENDIMENTOS a partir da base de agendamentos
    fetch_consultaja.py      busca a base de agendamentos direto na API da ConsultaJá (opcional, manual)
    fetch_indecx.py          busca a planilha de NPS de paciente direto na API do Indecx (opcional, manual)
    atualizar_local.py       orquestra só fetch_consultaja.py + update_attendance.py (superseded por atualizar_tudo.py)
    atualizar_tudo.py        orquestra as DUAS fontes num comando só -- reaproveita planilha ConsultaJá do
                              dia se agendas-pac-real (ou este) já tiver baixado
    comparar_planilhas.py    compara duas planilhas do Indecx célula a célula, sem expor dado sensível
    explore_planilha.py      explora estrutura de uma planilha nova sem expor dado de paciente
    attendance.py, transform.py, loaders.py, sanitize.py, render_script.py, config.py, indecx_client.py, consultaja_client.py
    atualizacoes.log         (gitignored) histórico local das execuções -- só contagens agregadas
    README.md                 como rodar cada script

  agendas-pac-real/     repositório irmão (git próprio) -- ver seu README.md e pipeline/README.md
  csat/                 repositório irmão (git próprio) -- ver seu README.md e pipeline/README.md
  agendas_pgmed/        repositório irmão (git próprio) -- ver seu README.md e pipeline/README.md
```

Não existe Node/build step -- é HTML/CSS/JS puro servido estaticamente. O Python do pipeline é só para regenerar os dados embutidos em `script.js`; o dashboard em si não depende de Python em tempo de execução.

## O que já está implementado

**Dashboard (`index.html`/`style.css`/`script.js`)**
- KPIs gerais (Visão geral): NPS Score, Respostas, Nota média, Promotores, Detratores, Engajamento.
- Seletor Tudo/Dia/Semana/Mês/Ano na Visão geral -- mostra o **período mais recente** daquela granularidade (não navega para períodos antigos ainda). Só afeta o KPI row, o resto do dashboard continua mostrando o total.
- Distribuição das respostas: donut por categoria NPS + barras por nota.
- Evolução ao longo do tempo: gráfico de linha com filtro Dia/Semana/Mês/Ano (independente do filtro da Visão geral).
- NPS por unidade, reação do comentário (classificação de sentimento do texto livre), lista de comentários com busca e filtro por categoria.
- Filtro global por unidade (topo da página) e tema claro/escuro.

**Pipeline Python**
- `main.py --source file --input planilha.xlsx` -- lê export do Indecx, gera `RECORDS`/`WEEKLY`.
- `update_attendance.py planilha.xlsx` -- lê a base de agendamentos, gera `ATENDIMENTOS`.
- `fetch_consultaja.py` -- busca agendas/agendamentos direto na API da ConsultaJá e salva o Excel em `dados-fonte/` (mesmo formato que já era exportado manualmente). Substitui só o passo de exportar a planilha à mão; o próximo passo continua sendo `update_attendance.py` no arquivo gerado. Roda só quando chamado manualmente -- não há agendador/cron configurado, por decisão consciente (cada resposta da API traz nome/celular de paciente).
- `atualizar_tudo.py` (chamado por `Atualizar Dashboard.bat`, na raiz) -- encadeia as duas fontes (ConsultaJá + Indecx) num só clique local: busca nas APIs (reaproveitando a planilha da ConsultaJá do dia se `agendas-pac-real` já tiver baixado), recalcula `ATENDIMENTOS`/`RECORDS`/`WEEKLY`, grava `script.js` e imprime um resumo (o que mudou, o que falhou se falhou). Se algo quebrar antes do passo de gravação, `script.js` não é tocado. O resumo também vai para `pipeline/atualizacoes.log` (gitignored) -- só contagens agregadas, nunca nome/celular de paciente.
- `render_script.py: upsert_const()` -- mecanismo genérico que substitui só a linha da constante de dados que está sendo atualizada, sem tocar no resto do `script.js` (gráficos/filtros intactos).
- Anonimização por lista de permissão: só os campos que o dashboard usa são extraídos; qualquer coluna de nome/e-mail/telefone/CPF/prontuário é descartada automaticamente, mesmo sem filtrar manualmente.
- `sanitize.py` varre o comentário livre e remove e-mail/CPF/telefone digitado por engano.

## Como cada número da "Visão geral" é calculado

Todos partem do mesmo conjunto de respostas: primeiro filtra por unidade (`filteredRecords()`), depois pelo período escolhido no chip Dia/Semana/Mês/Ano/Tudo (`computeOverviewStats()`, script.js).

- **Respostas** = contagem de respostas nesse conjunto.
- **Nota média** = média do campo `nota` (0–10).
- **Promotores / Detratores** = % de respostas com `categoria` = `promotor` / `detrator` (nota 9–10 = promotor, 7–8 = passivo, 0–6 = detrator).
- **NPS Score** = % promotores − % detratores.
- **Engajamento** = respostas de NPS ÷ atendimentos (`ATENDIMENTOS`, filtrado por `Status` = `Compareceu` ou
  `Atendido`) no
  **mesmo período e unidade**. O texto do card é sempre "[respostas de NPS] de [atendimentos]" -- não inverter
  a leitura (ex.: "6 de 164" = 6 respostas de NPS de um total de 164 atendimentos, não "6 atendimentos").
  No modo "Tudo" o período é o intervalo coberto por todas as respostas de NPS carregadas (`globalPeriodBounds()`)
  -- **esse período é sempre global, não é recalculado por unidade** mesmo se você
  filtrar por uma unidade específica. Já nos modos Dia/Semana/Mês/Ano, o período **é** recalculado com base na
  resposta de NPS mais recente *da unidade filtrada* (`computeOverviewStats()`, script.js) -- e é sempre a data
  da resposta de NPS que manda, nunca a data de atendimento.

## Decisões de negócio confirmadas

- **Engajamento -- status (revertido 08/09/2026)**: atendimento = `Status` `Compareceu` **ou** `Atendido`.
  `Atendido` é a nomenclatura antiga -- parou de ser usada em ago/2025 -- mas são visitas que realmente
  aconteceram, então contam também. Demais status (Cancelado, Faltou, Agendado, Confirmado) não contam.
- **Mapeamento de unidade (corrigido 04/09/2026)**: `São Paulo` (ConsultaJá) = `QUINTAL SLM - CONSOLAÇÃO` (NPS),
  `Campinas` = `QUINTAL SLM - CAMPINAS`, `Brasília` = `QUINTAL SLM - BRASÍLIA` -- ver `pipeline/attendance.py:
  UNIT_MAP`.
- **"Online" (decisão final 04/09/2026)**: fica de fora do agregado de Engajamento **por completo** -- são
  teleconsultas (Psiquiatria/Endocrinologia) sem divisão de filial, reportado no terminal ao rodar o
  pipeline, não descartado em silêncio.
- **Hospedagem pública, conta PG-MED-MANDIC (11/09/2026, migrada de TCM-18)**: repositório público no
  GitHub Free (Pages exige repo público nesse plano). Decisão consciente: histórico do repo e `script.js`
  ficam visíveis a qualquer pessoa -- nome/CPF/telefone/e-mail nunca entram no arquivo por design.
- **Workspace consolidado numa pasta só (15/09/2026)**: `agendas-pac-real`, `csat` e `agendas_pgmed` foram
  trazidos pra dentro de `NPS-PACIENTE` (cada um com git próprio) pra facilitar atualização e reaproveitar
  a planilha da ConsultaJá entre repositórios que usam a mesma conta. `troca-github` (workspace antigo) foi
  descontinuado.
- **`csat`: nomes de aluno no feedback completo são mantidos** (decisão do usuário, 15/09/2026) -- prática
  já existente desde 22/07/2026 (commit do usuário anterior, conta `TCM-18`), mantida como estava.

## Pendências / próximos passos

1. **`agendas-pac-real`**: verificar com quem administra a ConsultaJá por que a turma "Dermatologia
   Cirúrgica T2" (São Paulo) não aparece no nosso token/conta -- existe na versão de referência (TCM-18).
2. **`agendas_pgmed`**: decidir se querem a aba "💰 Turmas Pagas" (simulação de receita) que a versão de
   referência ganhou -- precisa da lista de quais turmas são pagas (não vem de planilha nenhuma) e de
   desenvolvimento novo (não é só ajuste de pipeline).
3. **`csat`**: dataset "NPS Pós-Médica" (`DATA_NPS`/`DATA_FEEDBACK_FULL`) continua sem pipeline automatizado
   -- pesquisa Indecx de origem (`groupId`/`actionId`) ainda não identificada. Também não sabemos ainda como
   a versão de referência gera esses dois datasets (não é o botão de upload da própria página).
4. **Navegação de períodos**: hoje o seletor Dia/Semana/Mês/Ano da Visão geral só mostra o período mais
   recente. Navegar pra períodos anteriores fica pra uma próxima iteração.
5. Se a base de agendamentos for atualizada (novo arquivo em `dados-fonte/`), rodar `atualizar_tudo.py` de
   novo. Não precisa rodar toda vez que só uma fonte mudar.
6. **`fetch_and_save()` (ConsultaJá) sobrescreve sem checar** se já existe arquivo com o mesmo nome no dia --
   cuidado ao colocar planilha manual em `dados-fonte/` com esse nome no dia de rodar o fetch.
7. **Segurança (achado, não corrigido)**: os outros 2 repositórios do workspace antigo que NÃO foram
   trazidos pra cá (`coord_mandic`, `score-operacional`) têm senha/e-mail de gestor fixos no código-fonte,
   em repositórios públicos -- ver `CONTEXTO-GITHUB.md`. Não é deste projeto, mas fica registrado.
