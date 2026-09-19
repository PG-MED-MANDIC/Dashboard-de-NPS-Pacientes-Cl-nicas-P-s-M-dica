"""Orquestrador da rotina diária automática (n8n), rodando os 4 pipelines +
publicando nos repositórios, sem intervenção humana. Criado em 2026-09-18 a
pedido do usuário, que decidiu conscientemente substituir a regra anterior
de "sem automação não supervisionada" por um agendamento fixo (ver
PROGRESSO.md e a memória rotina-atualizar-dashboards) -- a palavra-chave que
autoriza esse push automático já foi dada uma vez, aqui, não a cada rodada.

Uso (chamado pelo n8n via Execute Command, em dois horários diferentes --
decisão de 2026-09-18, porque checklist-captacao.xlsx só fica pronta no
SharePoint por volta das 10h):

    python atualizar_diario_n8n.py --repos raiz,csat,hub          # 06:00
    python atualizar_diario_n8n.py --repos agendas-pac-real,agendas_pgmed  # 10:30

Sem --repos, roda todos (uso manual/debug). Só imprime UMA linha em stdout:
um JSON com o resultado da rodada (pra o n8n parsear e montar o aviso do
Teams). Todo o log humano-legível vai pra `atualizacoes_diarias_n8n.log`,
nesta pasta.

Variáveis de ambiente (lidas de `.env` nesta pasta, se existir -- mesmo
esquema já usado em pipeline/.env pros tokens da ConsultaJá/Indecx; não
precisa configurar variável de ambiente do Windows):
- NPS_DASH_GITHUB_PAT: token do GitHub (fine-grained, "Contents: read and
  write" nos 5 repositórios em REPOS -- os 4 dashboards + Hub) usado só no
  comando `git push`, nunca gravado em disco além desse `.env` nem no remote
  `origin` -- se não estiver definida, o script commita localmente e avisa
  que o push foi pulado (não falha).
- NPS_CHECKLIST_MAX_DIAS (opcional, padrão 7): idade máxima em dias antes de
  avisar que checklist-captacao.xlsx (SharePoint, baixado manualmente) está
  desatualizado. Só avisa -- nunca baixa nem toca no SharePoint (isso
  continua manual, por decisão de 2026-09-15, ver
  agendas_pgmed/pipeline/README.md).
- NPS_TEAMS_WEBHOOK_URL: URL do webhook (Power Automate/Teams) que recebe o
  resumo da rodada. Sem ela, o script só não manda o aviso (não falha) --
  fica registrado em atualizacoes_diarias_n8n.log de qualquer forma.

Nota 2026-09-18: o plano original era o n8n chamar este script (Execute
Command) e montar/mandar o aviso do Teams num node "Code"+"HTTP Request"
próprios. A instância de n8n usada aqui não tem o node Execute Command
habilitado -- por isso a execução migrou pro Agendador de Tarefas do
Windows, e a montagem/envio da mensagem do Teams (antes no node Code)
passou pra dentro deste script (`montar_mensagem_teams`/`notificar_teams`).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Console do Windows/Agendador de Tarefas costuma anexar stdout/stderr com a
# codepage ANSI (cp1252) em vez de UTF-8 -- e o resumo dos pipelines (dado
# real da ConsultaJá/Indecx) tem acento e caracteres fora do cp1252. Sem
# isso, o print() final quebra com UnicodeEncodeError mesmo depois de tudo
# (pipelines, commit, push, aviso do Teams) já ter rodado com sucesso.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_ROOT = Path(__file__).resolve().parent
load_dotenv(WORKSPACE_ROOT / ".env")

LOG_PATH = WORKSPACE_ROOT / "atualizacoes_diarias_n8n.log"
CHECKLIST_PATH = WORKSPACE_ROOT / "dados-fonte" / "checklist-captacao.xlsx"
CHECKLIST_MAX_DIAS = int(os.environ.get("NPS_CHECKLIST_MAX_DIAS") or "7")
GITHUB_PAT = os.environ.get("NPS_DASH_GITHUB_PAT") or None
TEAMS_WEBHOOK_URL = os.environ.get("NPS_TEAMS_WEBHOOK_URL") or None
PIPELINE_TIMEOUT_S = 900

REPOS = [
    {
        "chave": "raiz",
        "dir": WORKSPACE_ROOT,
        "pipeline_dir": WORKSPACE_ROOT / "pipeline",
        "arquivos": ["index.html", "style.css", "script.js"],
        "mensagem": lambda d: f"Atualiza dados do dashboard ({d:%d.%m.%y})",
    },
    {
        "chave": "agendas-pac-real",
        "dir": WORKSPACE_ROOT / "agendas-pac-real",
        "pipeline_dir": WORKSPACE_ROOT / "agendas-pac-real" / "pipeline",
        "arquivos": ["index.html"],
        "mensagem": lambda d: f"Atualiza dados do dashboard ({d:%d.%m.%y})",
        "usa_checklist": True,
    },
    {
        "chave": "csat",
        "dir": WORKSPACE_ROOT / "csat",
        "pipeline_dir": WORKSPACE_ROOT / "csat" / "pipeline",
        "arquivos": ["index.html", "data.js"],
        "mensagem": lambda d: f"Atualiza dados do dashboard (CSAT por item, {d:%d.%m.%y})",
    },
    {
        "chave": "agendas_pgmed",
        "dir": WORKSPACE_ROOT / "agendas_pgmed",
        "pipeline_dir": WORKSPACE_ROOT / "agendas_pgmed" / "pipeline",
        "arquivos": ["index.html"],
        "mensagem": lambda d: f"Atualiza dados do dashboard ({d:%d.%m.%y})",
        "usa_checklist": True,
    },
    {
        # Sem pipeline -- só publica edição manual pendente no index.html (se
        # houver), decisão de 2026-09-18: o usuário aceita o risco de uma
        # edição em andamento ir ao ar sem revisão, por rodar só uma vez por
        # dia (06:00) e editar o hub fora desse horário.
        "chave": "hub",
        "dir": WORKSPACE_ROOT / "hub",
        "pipeline_dir": None,
        "arquivos": ["index.html"],
        "mensagem": lambda d: f"Atualiza hub ({d:%d.%m.%y})",
    },
]


def _log(lines: list[str]) -> None:
    text = "\n".join(lines) + "\n"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
        f.write(text)


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def checklist_status() -> dict:
    if not CHECKLIST_PATH.exists():
        return {"existe": False, "idade_dias": None, "aviso": "checklist-captacao.xlsx não encontrado em dados-fonte/ (SharePoint, baixado manualmente)."}
    idade_dias = (datetime.now().timestamp() - CHECKLIST_PATH.stat().st_mtime) / 86400
    aviso = None
    if idade_dias > CHECKLIST_MAX_DIAS:
        aviso = (
            f"checklist-captacao.xlsx desatualizado: {idade_dias:.0f} dia(s) sem baixar do "
            f"SharePoint (limite {CHECKLIST_MAX_DIAS}). Agendamentos/SLOTS calculados com base velha."
        )
    return {"existe": True, "idade_dias": round(idade_dias, 1), "aviso": aviso}


def run_pipeline(repo: dict) -> dict:
    pipeline_dir = repo["pipeline_dir"]
    try:
        proc = subprocess.run(
            [sys.executable, "atualizar_tudo.py"],
            cwd=pipeline_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=PIPELINE_TIMEOUT_S,
        )
        saida = proc.stdout + proc.stderr
        ok = proc.returncode == 0
    except subprocess.TimeoutExpired:
        saida = f"TIMEOUT após {PIPELINE_TIMEOUT_S}s"
        ok = False
    except Exception as e:  # nao deixar uma excecao derrubar a rodada inteira
        saida = f"ERRO ao chamar o pipeline: {e}"
        ok = False

    avisos_ok = [ln.strip() for ln in saida.splitlines() if ln.strip().startswith("OK --")]
    return {"ok": ok, "saida": saida, "resumo_ok": avisos_ok}


def commit_and_push(repo: dict, hoje: datetime) -> dict:
    repo_dir = repo["dir"]
    arquivos = repo["arquivos"]

    status = _git(["status", "--porcelain", "--", *arquivos], repo_dir)
    if not status.stdout.strip():
        return {"houve_alteracao": False, "push_ok": None, "erro": None, "mensagem": None}

    mensagem = repo["mensagem"](hoje)
    add = _git(["add", *arquivos], repo_dir)
    if add.returncode != 0:
        return {"houve_alteracao": True, "push_ok": False, "erro": f"git add falhou: {add.stderr}", "mensagem": mensagem}

    commit = _git(["commit", "-m", mensagem], repo_dir)
    if commit.returncode != 0:
        return {"houve_alteracao": True, "push_ok": False, "erro": f"git commit falhou: {commit.stderr}", "mensagem": mensagem}

    if not GITHUB_PAT:
        return {
            "houve_alteracao": True,
            "push_ok": False,
            "erro": "NPS_DASH_GITHUB_PAT não configurada -- commit feito localmente, push pulado.",
            "mensagem": mensagem,
        }

    remote = _git(["remote", "get-url", "origin"], repo_dir)
    origin_url = remote.stdout.strip()
    if not origin_url.startswith("https://"):
        return {"houve_alteracao": True, "push_ok": False, "erro": f"remote origin não é https, não sei autenticar: {origin_url}", "mensagem": mensagem}

    token_url = origin_url.replace("https://", f"https://x-access-token:{GITHUB_PAT}@", 1)
    push = _git(["push", token_url, "HEAD:main"], repo_dir)
    if push.returncode != 0:
        erro = push.stderr.replace(GITHUB_PAT, "***")
        return {"houve_alteracao": True, "push_ok": False, "erro": f"git push falhou: {erro}", "mensagem": mensagem}

    # Push foi pra uma URL direta (não pro remote "origin" nomeado), então o
    # git local não atualiza refs/remotes/origin/main sozinho -- sem isso,
    # "git status" mostraria "ahead 1" mesmo com o push já confirmado no
    # GitHub. Só bookkeeping local, não faz round-trip de rede.
    head = _git(["rev-parse", "HEAD"], repo_dir).stdout.strip()
    if head:
        _git(["update-ref", "refs/remotes/origin/main", head], repo_dir)

    return {"houve_alteracao": True, "push_ok": True, "erro": None, "mensagem": mensagem}


def atualizar_progresso_md(resultado: dict, hoje: datetime) -> bool:
    repos_com_mudanca = [r for r in resultado["repos"] if r["commit"]["houve_alteracao"]]
    avisos = [w for r in resultado["repos"] for w in r.get("avisos", [])]
    if resultado["checklist_captacao"] and resultado["checklist_captacao"]["aviso"]:
        avisos.append(resultado["checklist_captacao"]["aviso"])
    if not repos_com_mudanca and not avisos:
        return False

    linhas = [f"### Rodada de atualização ({hoje:%d/%m/%Y} {hoje:%H:%M}) -- automática via n8n", ""]
    if repos_com_mudanca:
        partes = []
        for r in repos_com_mudanca:
            resumo = "; ".join(r["resumo_ok"]) if r["resumo_ok"] else "sem detalhe"
            push_txt = "publicado" if r["commit"]["push_ok"] else "commitado localmente (push pendente)"
            partes.append(f"`{r['chave']}` ({resumo}) -- {push_txt}")
        linhas.append("Rodados e publicados automaticamente: " + "; ".join(partes) + ".")
    else:
        nomes = ", ".join(f"`{r['chave']}`" for r in resultado["repos"])
        linhas.append(f"Rodada automática sem alterações ({nomes}).")
    if avisos:
        linhas.append("")
        linhas.append("Avisos: " + " | ".join(avisos))
    linhas.append("")

    progresso_path = WORKSPACE_ROOT / "PROGRESSO.md"
    texto = progresso_path.read_text(encoding="utf-8")
    marcador = "## Próximo passo imediato (retomar daqui)"
    idx = texto.find(marcador)
    if idx == -1:
        return False
    # insere antes da rodada mais recente já registrada (mesma posição onde cada
    # rodada manual nova entrava até agora), nunca antes dela
    pos_primeira_rodada = texto.find("### Rodada de atualização", idx)
    if pos_primeira_rodada == -1:
        return False
    novo_texto = texto[:pos_primeira_rodada] + "\n".join(linhas) + "\n" + texto[pos_primeira_rodada:]
    progresso_path.write_text(novo_texto, encoding="utf-8")
    return True


def montar_mensagem_teams(resultado: dict) -> list[str]:
    """Mesma lógica que estava no node "Code" do n8n (JS) -- portada pra
    Python porque a execução deixou de passar pelo n8n (node Execute Command
    não existe nessa instância). Devolve uma linha por item (vira um
    TextBlock por linha no Adaptive Card, ver notificar_teams())."""
    linhas = []
    if resultado["sucesso_geral"]:
        linhas.append(f"✅ **Rotina dos dashboards NPS-PACIENTE** ({resultado['data']} {resultado['hora']})")
    else:
        linhas.append(f"⚠️ **Rotina dos dashboards NPS-PACIENTE com falha em algum pipeline** ({resultado['data']} {resultado['hora']})")

    for repo in resultado["repos"]:
        status = "OK" if repo["pipeline_ok"] else "FALHOU"
        commit = repo.get("commit") or {}
        if commit.get("houve_alteracao"):
            if commit.get("push_ok"):
                publicacao = "publicado"
            else:
                publicacao = "commitado localmente, push pendente"
                if commit.get("erro"):
                    publicacao += f" ({commit['erro']})"
        else:
            publicacao = "sem alteração"
        resumo = "; ".join(repo.get("resumo_ok") or []) or "; ".join(repo.get("avisos") or [])
        linha = f"- **{repo['chave']}** [{status}] {publicacao}"
        if resumo:
            linha += f" -- {resumo}"
        linhas.append(linha)

    if resultado["checklist_captacao"] and resultado["checklist_captacao"].get("aviso"):
        linhas.append("")
        linhas.append(f"⚠️ {resultado['checklist_captacao']['aviso']}")

    return linhas


def _montar_adaptive_card(linhas: list[str]) -> dict:
    """O fluxo do Power Automate ("Enviar alertas webhook para um canal")
    joga o corpo INTEIRO do POST direto num Adaptive Card (variável "Body" =
    triggerBody() bruto) -- não é {"text": ...} como um webhook clássico do
    Teams. Descoberto em 2026-09-19 depois do primeiro teste real dar
    InvalidBotAdaptiveCard: sem isso, qualquer JSON que não seja um Adaptive
    Card válido quebra a postagem."""
    corpo = [
        {"type": "TextBlock", "text": linha, "wrap": True} if linha.strip() else {"type": "TextBlock", "text": " "}
        for linha in linhas
    ]
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": corpo,
    }


def notificar_teams(linhas: list[str]) -> dict:
    if not TEAMS_WEBHOOK_URL:
        return {"enviado": False, "erro": "NPS_TEAMS_WEBHOOK_URL não configurada -- aviso não enviado."}
    card = _montar_adaptive_card(linhas)
    body = json.dumps(card).encode("utf-8")
    req = urllib.request.Request(
        TEAMS_WEBHOOK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {"enviado": True, "status": resp.status, "erro": None}
    except urllib.error.HTTPError as e:
        return {"enviado": False, "erro": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:500]}"}
    except Exception as e:
        return {"enviado": False, "erro": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repos",
        help="Chaves separadas por vírgula (ex.: raiz,csat,hub). Sem isso, roda todos.",
        default=None,
    )
    args = parser.parse_args()

    if args.repos:
        chaves = {c.strip() for c in args.repos.split(",") if c.strip()}
        repos_a_rodar = [r for r in REPOS if r["chave"] in chaves]
        desconhecidas = chaves - {r["chave"] for r in REPOS}
        if desconhecidas:
            print(f"Aviso: chave(s) desconhecida(s) em --repos, ignorada(s): {', '.join(sorted(desconhecidas))}", file=sys.stderr)
    else:
        repos_a_rodar = REPOS

    hoje = datetime.now()
    resultado: dict = {
        "data": f"{hoje:%Y-%m-%d}",
        "hora": f"{hoje:%H:%M}",
        "checklist_captacao": checklist_status() if any(r.get("usa_checklist") for r in repos_a_rodar) else None,
        "repos": [],
    }

    for repo in repos_a_rodar:
        item = {"chave": repo["chave"]}
        if repo["pipeline_dir"] is not None:
            pipeline = run_pipeline(repo)
            item["pipeline_ok"] = pipeline["ok"]
            item["resumo_ok"] = pipeline["resumo_ok"]
            item["saida_completa"] = pipeline["saida"]
            item["avisos"] = [ln.strip() for ln in pipeline["saida"].splitlines() if "aviso" in ln.lower() or "falhou" in ln.lower()]
        else:
            # sem pipeline (Hub): não há dado pra buscar, só publica o que já
            # estiver salvo no arquivo (edição manual)
            item["pipeline_ok"] = True
            item["resumo_ok"] = []
            item["saida_completa"] = ""
            item["avisos"] = []

        if item["pipeline_ok"]:
            item["commit"] = commit_and_push(repo, hoje)
        else:
            item["commit"] = {"houve_alteracao": False, "push_ok": None, "erro": "pipeline falhou, commit pulado", "mensagem": None}

        resultado["repos"].append(item)

    resultado["sucesso_geral"] = all(r["pipeline_ok"] for r in resultado["repos"])
    resultado["progresso_md_atualizado"] = atualizar_progresso_md(resultado, hoje)

    mensagem_teams = montar_mensagem_teams(resultado)
    resultado["teams"] = notificar_teams(mensagem_teams)

    log_linhas = [f"sucesso_geral={resultado['sucesso_geral']}", "", "--- mensagem Teams ---", *mensagem_teams, f"envio: {resultado['teams']}"]
    for r in resultado["repos"]:
        log_linhas.append(f"\n--- {r['chave']} ---")
        log_linhas.append(r["saida_completa"])
        log_linhas.append(f"commit: {r['commit']}")
    _log(log_linhas)

    # stdout: só o JSON, numa linha, pro n8n parsear
    resultado_para_n8n = {k: v for k, v in resultado.items()}
    for r in resultado_para_n8n["repos"]:
        r.pop("saida_completa", None)
    print(json.dumps(resultado_para_n8n, ensure_ascii=False))

    # Sempre 0: falha de pipeline já está sinalizada em sucesso_geral/avisos no
    # JSON acima -- é isso que o n8n usa pra montar o aviso do Teams. Um
    # returncode != 0 faria o node "Execute Command" do n8n tratar isso como
    # erro de execução (não de dado) e podia engolir o aviso antes de chegar
    # no Teams.
    return 0


if __name__ == "__main__":
    sys.exit(main())
