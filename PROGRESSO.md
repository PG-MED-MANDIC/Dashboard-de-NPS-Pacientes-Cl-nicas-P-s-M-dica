# Progresso — Dashboard de NPS (SLMandic)

Documento de continuidade: estado atual do projeto, decisões tomadas e o que falta. Última atualização: 2026-09-04.

## Próximo passo imediato (retomar daqui)

**Pipeline validado, dados publicados no repositório público, regra de Engajamento corrigida e simplificada
hoje (04/09/2026). Falta só ativar o GitHub Pages (ver seção "Hospedagem" abaixo).**

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
  propósito). `Atualizar Dashboard.bat` (raiz) chama esse mesmo script -- duplo clique faz tudo. Passo a passo
  completo (sem precisar do assistente) está em `COMO_ATUALIZAR.txt` (raiz, não versionado -- é só lembrete
  local).
- **Bug do Engajamento corrigido (04/09/2026)**: ver "Decisões de negócio confirmadas" e commits `9e7b974` /
  `061ef4a`. Resumo: nome de unidade estava desatualizado (Indecx passou a exportar com prefixo "QUINTAL SLM -")
  e a regra de status foi simplificada pra só `Compareceu`.
- **Dados atuais em `script.js`** (gravados em 08/09/2026): 144 respostas de NPS → 13 semanas; `ATENDIMENTOS`
  com 750 combinações dia+unidade, 23.042 atendimentos (`Compareceu` + `Atendido`, só as 3 unidades físicas, sem
  "Online").
  Aviso de sanitização de um CPF digitado por engano num comentário (unidade QUINTAL SLM - BRASÍLIA, 06/08/2026)
  removido automaticamente pelo `sanitize.py` -- confirmado que só `[removido]` entrou no arquivo.
- **29 das 144 respostas de NPS vêm com `unidade` em branco** (dado assim na origem, não é bug do pipeline) --
  espalhadas de 10/06 a 03/09/2026, quase todas nota 9-10. Entram no total geral ("Tudo"/sem filtro), mas somem
  se alguém filtrar por uma unidade específica. Causa ainda não confirmada (possível canal de pesquisa que não
  pergunta a unidade) -- perguntar pra quem administra o Indecx se quiser investigar.

### Hospedagem: público no GitHub Free, já com push feito (04/09/2026)

Testamos repositório privado na conta pessoal em 03/09: o GitHub exige plano pago (Pro/Team/Enterprise Cloud)
pra usar Pages com repo privado. Repositório pessoal antigo foi apagado.

**Decisão do usuário (04/09/2026): seguir com GitHub Free mesmo, repositório público.** Ciente do trade-off --
diferente de um repo privado, isso expõe o histórico de commits e o `script.js` completo (notas + comentários
de pacientes, já anonimizados) para qualquer pessoa na internet. Mitigação: manter só
nota/data/hora/unidade/comentário/reação (nunca nome/endereço/CPF/telefone -- já é assim por design, ver
"Anonimização por lista de permissão" abaixo) e revisamos o histórico do git antes do primeiro push (sem
CPF/e-mail nem `.env`/`.xlsx` commitado em nenhum commit).

Repositório: `Caio-Baldin/Dashboard-de-NPS-Pacientes-Cl-nicas-P-s-M-dica`, remoto `origin` configurado, **já
com 3 pushes feitos** (`b05d903` dados+END_DATE dinâmico, `9e7b974` e `061ef4a` correções de Engajamento).
**Falta confirmar se o GitHub Pages já foi ativado** em Settings → Pages, branch `main` -- não foi feito pelo
assistente nesta sessão, verificar com o usuário.

Confirmado em sessão anterior (31/08/2026): `ATENDIMENTOS` (ConsultaJá → card "Engajamento") e `RECORDS`/`WEEKLY`
(Indecx → NPS Score/Respostas/Nota média/Promotores/Detratores) são fontes **completamente independentes** --
rodar um pipeline não atualiza o outro. Ver `script.js:30-53` (`computeStats()` usa `RECORDS`, `computeEngajamento()`
usa `ATENDIMENTOS`).

**Planilhas brutas em `dados-fonte/` são apagadas rotineiramente** depois de usadas (comparação/validação) --
não ficam acumulando. Na sessão de 04/09/2026 foram baixadas, comparadas com export manual, e depois apagadas
duas vezes (o usuário pediu explicitamente pra apagar entre uma rodada e outra). Se `dados-fonte/*.xlsx` estiver
vazio quando retomar, é esperado -- não é perda de dado, é rodar `atualizar_tudo.py` (ou o `.bat`) de novo pra
gerar planilhas atuais.

`codigo-consultaja.txt` (rascunho do script original, que ficava na raiz) **foi apagado** -- toda a lógica dele já
está em `pipeline/consultaja_client.py`/`fetch_consultaja.py`, então não fazia mais falta.

## Estrutura do projeto

```
index.html          estrutura da página
style.css            tema navy/gold, claro/escuro
script.js            dados embutidos (RECORDS/WEEKLY/ATENDIMENTOS) + toda a lógica de gráficos/filtros
README.md            visão geral do dashboard + fluxo de atualização/publicação
.gitignore            raiz do projeto -- protege .env, dado bruto, .venv, log local (ver seção de segurança abaixo)
Atualizar Dashboard.bat   atalho local: roda atualizar_tudo.py (as duas fontes) e mostra o resumo
COMO_ATUALIZAR.txt   passo a passo de atualização/publicação pro usuário rodar sozinho (não versionado)

dados-fonte/          planilhas brutas (gitignored -- nunca versionar/hospedar)
  Base_Consulta_Ja26_08_28.xlsx, Base_Consulta_Ja26_08_30.xlsx, ...   base de agendamentos (uma por execução, geradas por fetch_consultaja.py), usada só pelo Engajamento

pipeline/             scripts Python que regeneram os dados de script.js
  main.py                  RECORDS/WEEKLY a partir de export do Indecx (planilha em mãos ou baixada via API)
  update_attendance.py     ATENDIMENTOS a partir da base de agendamentos
  fetch_consultaja.py      busca a base de agendamentos direto na API da ConsultaJá (opcional, manual)
  fetch_indecx.py          busca a planilha de NPS de paciente direto na API do Indecx (opcional, manual)
  atualizar_local.py       orquestra só fetch_consultaja.py + update_attendance.py (não é mais chamado pelo .bat -- superseded por atualizar_tudo.py, mas continua funcionando se quiser só a parte de atendimentos)
  atualizar_tudo.py        orquestra as DUAS fontes (ConsultaJá + Indecx) num comando só -- python pipeline/atualizar_tudo.py
  comparar_planilhas.py    compara duas planilhas do Indecx célula a célula, sem expor dado sensível (validação)
  explore_planilha.py      explora estrutura de uma planilha nova sem expor dado de paciente
  attendance.py, transform.py, loaders.py, sanitize.py, render_script.py, config.py, indecx_client.py, consultaja_client.py
  atualizacoes.log         (gitignored) histórico local das execuções -- só contagens agregadas
  README.md                 como rodar cada script
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
- `atualizar_tudo.py` (chamado por `Atualizar Dashboard.bat`, na raiz) -- encadeia as duas fontes (ConsultaJá + Indecx) num só clique local: busca nas APIs, recalcula `ATENDIMENTOS`/`RECORDS`/`WEEKLY`, grava `script.js` e imprime um resumo (o que mudou, o que falhou se falhou). Se algo quebrar antes do passo de gravação, `script.js` não é tocado. O resumo também vai para `pipeline/atualizacoes.log` (gitignored) -- só contagens agregadas, nunca nome/celular de paciente. (`atualizar_local.py` é a versão antiga, só ConsultaJá -- não é mais chamada pelo `.bat`.)
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
  No modo "Tudo" o período é o intervalo coberto por todas as respostas de NPS carregadas (`globalPeriodBounds()`,
  hoje: 10/jun–04/set/2026) -- **esse período é sempre global, não é recalculado por unidade** mesmo se você
  filtrar por uma unidade específica. Já nos modos Dia/Semana/Mês/Ano, o período **é** recalculado com base na
  resposta de NPS mais recente *da unidade filtrada* (`computeOverviewStats()`, script.js) -- e é sempre a data
  da resposta de NPS que manda, nunca a data de atendimento. Por isso o % muda bastante entre "Tudo" e "Ano"
  mesmo com o mesmo numerador, e por isso um bug de nome de unidade divergente quebrava silenciosamente o
  denominador (ver "Decisões de negócio confirmadas").

## Decisões de negócio confirmadas

- **Engajamento -- status (revertido 08/09/2026)**: atendimento = `Status` `Compareceu` **ou** `Atendido`.
  `Atendido` é a nomenclatura antiga -- parou de ser usada em ago/2025 (ex.: Campinas, `Atendido` vai só até
  23/08/2025; `Compareceu` cobre de 09/01/2025 até hoje) -- mas são visitas que realmente aconteceram, então
  contam também. No dia 04/09/2026 tinha sido simplificado pra só `Compareceu`; revertido porque isso descartava
  o histórico de atendimentos de antes de ago/2025. Demais status (Cancelado, Faltou, Agendado, Confirmado) não
  contam.
- **Mapeamento de unidade (corrigido 04/09/2026)**: `São Paulo` (ConsultaJá) = `QUINTAL SLM - CONSOLAÇÃO` (NPS),
  `Campinas` = `QUINTAL SLM - CAMPINAS`, `Brasília` = `QUINTAL SLM - BRASÍLIA` -- ver `pipeline/attendance.py:
  UNIT_MAP`. **Bug histórico**: até 04/09/2026 o mapa apontava pro nome sem o prefixo "QUINTAL SLM -" (ex.: só
  `CONSOLAÇÃO`), porque o Indecx passou a exportar a unidade com esse prefixo em algum momento depois de
  31/08/2026 sem o pipeline ser atualizado junto. Como `script.js` compara os nomes exatamente iguais
  (`a.unidade===currentUnit`), o card de Engajamento sempre mostrava "Sem dados de atendimento" ao filtrar por
  qualquer unidade física específica (não só um dia -- qualquer período). Corrigido; ver commit `9e7b974`.
- **"Online" (decisão final 04/09/2026)**: fica de fora do agregado de Engajamento **por completo** (não conta
  nem no total geral "Tudo", não só ao filtrar por unidade) -- é reportado no terminal ao rodar o pipeline, não
  descartado em silêncio. Motivo: são teleconsultas (Psiquiatria/Endocrinologia) sem divisão de filial -- "esse
  Online engloba todas as filiais" (palavras do usuário), então não faz sentido atribuir a uma unidade nem
  somar ao geral sem contexto. Tentativa intermediária nesta sessão (contar Online só no total "Tudo", mantendo
  fora do filtro por unidade) foi revertida a pedido do usuário -- ver commit `061ef4a`.

## Pendências / próximos passos

1. **API do Indecx**: resolvida (03/09/2026) e em uso rotineiro desde então -- `indecx_client.py` é implementação real, `.env` preenchido, validada contra export manual mais de uma vez (0 diferenças). O caminho por planilha exportada manualmente (`main.py --source file`) continua funcionando como alternativa/fallback.
2. **Hospedagem**: decidida em 04/09/2026 -- **repositório público no GitHub Free** (ver "Próximo passo imediato" no topo deste arquivo). Testamos repositório privado na conta pessoal antes; o GitHub exige plano pago pra Pages com repo privado. Decisão consciente do usuário: seguir público mesmo, aceitando que o histórico do repo e o `script.js` (notas + comentários já anonimizados) ficam visíveis a qualquer pessoa -- nome/endereço/CPF/telefone nunca entram no arquivo (lista de permissão por coluna, ver `pipeline/config.py`). Continua não hospedando em serviços externos como Vercel/Netlify/Hostinger -- GitHub Pages é o único ambiente usado.
   - **Descartado por decisão consciente**: um botão dentro da própria página publicada que chamasse a API da ConsultaJá ao vivo (exigiria token exposto no navegador a qualquer visitante) e atualização automática/agendada rodando sozinha sem supervisão (exigiria um backend em ambiente interno, autenticação no endpoint e alinhamento prévio com a TI). Ver Plano A abaixo, que evita os dois problemas.
3. **Navegação de períodos**: hoje o seletor Dia/Semana/Mês/Ano da Visão geral só mostra o período mais recente. Se quiser navegar para períodos anteriores (setas ‹ ›), fica para uma próxima iteração -- foi a opção descartada quando perguntei.
4. Se a base de agendamentos for atualizada (novo arquivo em `dados-fonte/`), rodar `update_attendance.py` de novo para atualizar `ATENDIMENTOS`. Não precisa rodar toda vez que `RECORDS` muda -- só quando a planilha de agendamentos mudar.
5. **API da ConsultaJá -- resolvida e em uso** desde 30-31/08/2026, `.bat` já rodado várias vezes pelo próprio
   usuário (não só pelo assistente). Continua manual de propósito (nenhum agendador/cron -- cada resposta da
   API traz nome/celular de paciente). Token só em `pipeline/.env` (nunca commitado).
   - **Bug conhecido, ainda não corrigido**: `fetch_and_save()` grava em `dados-fonte/Base_Consulta_JaAA_MM_DD.xlsx`
     sem checar se o arquivo já existe -- sobrescreve silenciosamente. Cuidado ao colocar arquivos manuais em
     `dados-fonte/` com esse mesmo nome no dia em que for rodar o fetch.
   - Único ponto solto: `atualizacoes.log` não captura as linhas soltas de aviso que `fetch_consultaja.py`/
     `update_attendance.py` imprimem no console (ex.: aviso de unidades sem correspondente). Cosmético, não afeta
     o dado gravado em `script.js`.
