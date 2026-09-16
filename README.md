# Dashboard de NPS — Pacientes Clínicas Pós-Médica (SLMandic)

Dashboard estático (HTML + CSS + JS puro, sem dependências além das fontes do Google Fonts) com os dados da pesquisa de NPS por QR code. Publicado no GitHub Pages -- link e os outros 3 dashboards do workspace estão reunidos no hub: `https://pg-med-mandic.github.io/Hub/`.

## Arquivos

- `index.html` — estrutura da página
- `style.css` — estilos (tema navy/gold SLMandic, com suporte a modo claro/escuro)
- `script.js` — dados da pesquisa (embutidos como JSON) + lógica dos gráficos e filtros

## Atualizar os dados e publicar

O dado sempre é atualizado **localmente primeiro**; só depois o resultado
(já estático e anonimizado) é publicado. Nunca há chamada de API a partir da
página publicada.

1. Dê dois cliques em **`Atualizar Dashboard.bat`** (raiz do projeto), ou rode
   `python pipeline/atualizar_tudo.py`. Ele busca as duas fontes (ConsultaJá →
   `ATENDIMENTOS`, Indecx → `RECORDS`/`WEEKLY`) e regrava `script.js` -- ver
   `pipeline/README.md`.
2. Leia o resumo que aparece no final: quantas respostas/atendimentos antes e
   depois, e se algum passo falhou. Se algo quebrou **antes** do passo de
   gravação, `script.js` não foi alterado -- corrija o problema (normalmente
   `pipeline/.env` sem token válido) e rode de novo. O histórico de execuções
   fica em `pipeline/atualizacoes.log` (só contagens agregadas, nunca dado de
   paciente).
3. Confira o que mudou antes de publicar:
   ```
   git status
   git diff -- script.js
   ```
4. Suba só os arquivos estáticos -- **nunca use `git add .` ou `git add -A`
   aqui**, para não arriscar versionar `dados-fonte/`, `pipeline/.env` ou o
   `.venv` (o `.gitignore` do projeto já bloqueia isso, mas manter o hábito
   de listar os arquivos é uma segunda camada de proteção):
   ```
   git add index.html style.css script.js
   git commit -m "Atualiza dados do dashboard (AAAA-MM-DD)"
   git push
   ```

## Hospedagem

Repositório **público** no GitHub (conta `PG-MED-MANDIC`), com **GitHub
Pages ativado** (Settings → Pages → branch `main` → `/root`) -- decisão
consciente registrada em `PROGRESSO.md` > "Decisões de negócio confirmadas":
nome/CPF/telefone/e-mail nunca entram em `script.js` por design, então o
conteúdo publicado já nasce anonimizado.

Este repositório é um de 5 que vivem juntos nesta pasta (`NPS-PACIENTE`) só
por conveniência de workspace, cada um com seu próprio `.git`/remoto -- ver
`PROGRESSO.md` > "Mudança de estrutura importante".

## Sobre os dados

Os dados em `script.js` já passaram por uma etapa de anonimização: os campos de nome, e-mail, telefone, CPF e número de prontuário foram removidos, e um número de telefone digitado por engano no campo de comentário livre foi apagado. Ainda assim, os comentários de texto livre são reais (falas de pacientes) — trate este conteúdo como informação institucional sensível.
