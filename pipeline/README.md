# Pipeline de atualização de dados (Python)

Scripts para regenerar as constantes de dados em `../script.js`, a partir
de duas fontes independentes:

- **`RECORDS`/`WEEKLY`** -- respostas de NPS de paciente, via API do Indecx.
- **`ATENDIMENTOS`** -- base de agendamentos (ConsultaJá), usada pelo card
  "Engajamento" (respostas de NPS / atendimentos no mesmo período).

## Uso: um comando só

```
cd pipeline
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python atualizar_tudo.py
```

Ou duplo clique em `Atualizar Dashboard.bat`, na raiz do projeto -- chama
o mesmo script. Busca as duas fontes, recalcula os dados e regrava
`script.js`, imprimindo um resumo (também salvo em
`pipeline/atualizacoes.log`).

Antes de chamar a API da ConsultaJá, reaproveita a planilha do dia se ela
já tiver sido baixada (por este pipeline ou pelo pipeline vizinho
`agendas-pac-real/`, que compartilha a mesma pasta `dados-fonte/`) -- assim
as duas atualizações não baixam a mesma base duas vezes.

Não faz `git add`/`commit`/`push` -- isso continua manual de propósito,
pra sempre ter uma revisão humana antes de publicar:

```
git status
git add index.html style.css script.js
git commit -m "Atualiza dados do dashboard"
git push
```

Nunca use `git add -A`/`git add .` -- sempre a lista explícita acima, pra
não arriscar subir nada sensível por engano.

## Configuração

`indecx_client.py` é um **template**, não uma conexão pronta -- confirme
com a TI se a integração está autorizada e peça a documentação oficial da
API (endpoint, autenticação, paginação) antes de usar com dado real de
paciente; os pontos que precisam de revisão estão marcados com `TODO`.

`consultaja_client.py` já foi validado contra a API real. Copie
`.env.example` para `.env` e preencha `CONSULTAJA_TOKEN` (datas são
opcionais, `config.py` calcula sozinho) e as credenciais do Indecx.
**Nunca commite o `.env`.**

Por decisão consciente, nenhuma das duas buscas roda sem supervisão (sem
agendador/cron) -- cada resposta traz nome/celular/comentário de
paciente, então cada execução é uma decisão de quem está rodando.

## Regras de negócio confirmadas com o time

- "Atendimento" (`ATENDIMENTOS`) = linhas com `Status` em `Compareceu` ou
  `Atendido`. Os demais status (`Cancelado`, `Faltou`, `Agendado`,
  `Confirmado`) não contam.
- Mapeamento de unidade: `São Paulo` (agendamentos) = `CONSOLAÇÃO` (NPS).
  `Online` não tem correspondente no NPS hoje e fica fora do agregado por
  unidade (mas é reportado no terminal, não descartado em silêncio).
- O dashboard calcula o % de engajamento no navegador, comparando
  `ATENDIMENTOS` com o período coberto por `RECORDS` no momento da visita
  -- não precisa rodar de novo só porque `RECORDS` mudou, só quando a
  planilha de agendamentos for atualizada.

## O que o pipeline garante

- **Anonimização por lista de permissão** (`COLUMN_ALIASES` em
  `config.py`): só os campos que o dashboard usa são extraídos -- qualquer
  coluna de nome/e-mail/telefone/CPF/prontuário na planilha/API é
  descartada automaticamente. O mesmo vale para a base de agendamentos: só
  `Data`/`Status`/`Unidade` são lidos -- `Paciente`/`Celular`/`Profissional`
  nunca entram no agregado.
- **Sanitização do texto livre** (`sanitize.py`): remove padrões de
  e-mail/CPF/telefone que o paciente tenha digitado por engano dentro do
  comentário, e avisa no terminal (sem expor o dado) para revisão manual.
- **Regravação cirúrgica** (`render_script.py`): `upsert_const()` substitui
  só a linha da constante de dados que está sendo atualizada -- o resto do
  arquivo (gráficos, filtros, tema) não é tocado.
