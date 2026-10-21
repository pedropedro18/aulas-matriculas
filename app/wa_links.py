"""
Painel de administração + envio de aulas por WhatsApp SEM chave do Meta (links wa.me).
Abre: https://O-TEU-SERVICO.onrender.com/admin?chave=A_TUA_ADMIN_KEY
"""
import os
import re
import secrets
from datetime import datetime
from html import escape
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from .config import NIVEIS
from .db import Session, Aluno, Aula

router = APIRouter()

ADMIN_KEY = os.getenv("ADMIN_KEY", "")
DEFAULT_COUNTRY_CODE = os.getenv("DEFAULT_COUNTRY_CODE", "244")  # Angola


# ---------- utilitários ----------
def normalizar_numero(numero: str) -> str:
    digitos = re.sub(r"\D", "", numero or "")
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if len(digitos) == 9:  # número local sem indicativo
        digitos = DEFAULT_COUNTRY_CODE + digitos
    return digitos


def gerar_link_whatsapp(numero: str, mensagem: str) -> str:
    return f"https://wa.me/{normalizar_numero(numero)}?text={quote(mensagem)}"


def mensagem_aula(nome: str, aula: Aula) -> str:
    texto = (
        f"Olá {nome or ''}! Lembrete: aula de inglês ({aula.nivel}) "
        f"no dia {aula.inicio:%d/%m} às {aula.inicio:%H:%M}."
    )
    if aula.link:
        texto += f"\nLink: {aula.link}"
    return texto + "\nAté já!"


def verificar_chave(chave: str):
    if not ADMIN_KEY:
        raise HTTPException(503, "Define a variável ADMIN_KEY no Render.")
    if not secrets.compare_digest(chave or "", ADMIN_KEY):
        raise HTTPException(403, "Chave inválida.")


def voltar(chave: str, msg: str = ""):
    return RedirectResponse(f"/admin?chave={quote(chave)}&msg={quote(msg)}", status_code=303)


# ---------- ações ----------
@router.post("/admin/aluno")
def adicionar_aluno(
    chave: str = Form(""),
    nome: str = Form(...),
    telefone: str = Form(...),
    nivel: str = Form(...),
):
    verificar_chave(chave)
    tel = normalizar_numero(telefone)
    nivel = nivel.upper()
    if nivel not in NIVEIS or len(tel) < 9:
        return voltar(chave, "Dados inválidos.")
    with Session() as db:
        aluno = db.scalar(select(Aluno).where(Aluno.telefone == tel))
        if aluno is None:
            aluno = Aluno(telefone=tel)
            db.add(aluno)
        aluno.nome = nome.strip().title()
        aluno.nivel = nivel
        aluno.estado = "ativo"
        aluno.pago = True
        db.commit()
    return voltar(chave, "Aluno guardado ✅")


@router.post("/admin/aula")
def criar_aula(
    chave: str = Form(""),
    nivel: str = Form(...),
    data: str = Form(...),   # AAAA-MM-DD
    hora: str = Form(...),   # HH:MM
    link: str = Form(""),
):
    verificar_chave(chave)
    nivel = nivel.upper()
    try:
        inicio = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M")
    except ValueError:
        return voltar(chave, "Data ou hora inválida.")
    if nivel not in NIVEIS:
        return voltar(chave, "Nível inválido.")
    with Session() as db:
        db.add(Aula(nivel=nivel, inicio=inicio, link=link.strip()))
        db.commit()
    return voltar(chave, "Aula agendada ✅")


@router.post("/admin/aula/apagar")
def apagar_aula(chave: str = Form(""), aula_id: int = Form(...)):
    verificar_chave(chave)
    with Session() as db:
        aula = db.get(Aula, aula_id)
        if aula:
            db.delete(aula)
            db.commit()
    return voltar(chave, "Aula apagada.")


# ---------- página ----------
@router.get("/admin", response_class=HTMLResponse)
@router.get("/enviar-aulas", response_class=HTMLResponse)
def painel(chave: str = Query(""), msg: str = Query("")):
    verificar_chave(chave)
    k = escape(chave)
    agora = datetime.now(ZoneInfo("Africa/Luanda")).replace(tzinfo=None)
    opcoes = "".join(f"<option>{escape(n)}</option>" for n in NIVEIS)

    blocos = []
    with Session() as db:
        aulas = db.scalars(
            select(Aula).where(Aula.inicio >= agora).order_by(Aula.inicio)
        ).all()
        for aula in aulas:
            alunos = db.scalars(
                select(Aluno).where(Aluno.nivel == aula.nivel, Aluno.estado == "ativo")
            ).all()
            itens = "".join(
                f"<li><span>{escape(a.nome or a.telefone)}</span>"
                f'<a class="btn" href="{escape(gerar_link_whatsapp(a.telefone, mensagem_aula(a.nome, aula)))}" '
                'target="_blank" rel="noopener">Enviar</a></li>'
                for a in alunos
            ) or "<li>Sem alunos ativos neste nível.</li>"
            blocos.append(
                f"<h3>{escape(aula.nivel)} · {aula.inicio:%d/%m %H:%M}</h3>"
                f"<ul>{itens}</ul>"
                f'<form method="post" action="/admin/aula/apagar">'
                f'<input type="hidden" name="chave" value="{k}">'
                f'<input type="hidden" name="aula_id" value="{aula.id}">'
                f'<button class="del">Apagar aula</button></form>'
            )
        total_alunos = len(db.scalars(select(Aluno).where(Aluno.estado == "ativo")).all())

    corpo = "".join(blocos) or "<p>Sem aulas agendadas.</p>"
    aviso = f'<p class="msg">{escape(msg)}</p>' if msg else ""
    return f"""<!doctype html>
<html lang="pt"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Admin · Teacher Pedro</title>
<style>
 body{{font-family:system-ui,sans-serif;max-width:560px;margin:20px auto;padding:0 16px}}
 form.card{{display:grid;gap:8px;padding:14px;border:1px solid #ddd;border-radius:10px;margin:12px 0}}
 input,select,button{{padding:10px;font-size:16px;border-radius:8px;border:1px solid #bbb}}
 button{{background:#111;color:#fff;border:0}}
 button.del{{background:#c0392b;font-size:13px;padding:6px 10px}}
 ul{{list-style:none;padding:0;margin:6px 0}}
 li{{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #eee}}
 a.btn{{background:#25d366;color:#fff;padding:8px 14px;border-radius:8px;text-decoration:none}}
 .msg{{background:#eafaf1;padding:10px;border-radius:8px}}
</style></head><body>
<h2>Admin · Teacher Pedro</h2>{aviso}
<p>Alunos ativos: <b>{total_alunos}</b></p>

<h3>Adicionar aluno</h3>
<form class="card" method="post" action="/admin/aluno">
 <input type="hidden" name="chave" value="{k}">
 <input name="nome" placeholder="Nome completo" required>
 <input name="telefone" placeholder="Telefone (ex.: 923456789)" inputmode="tel" required>
 <select name="nivel">{opcoes}</select>
 <button>Guardar aluno</button>
</form>

<h3>Agendar aula</h3>
<form class="card" method="post" action="/admin/aula">
 <input type="hidden" name="chave" value="{k}">
 <select name="nivel">{opcoes}</select>
 <input type="date" name="data" required>
 <input type="time" name="hora" required>
 <input name="link" placeholder="Link da aula (Meet/Zoom)">
 <button>Agendar aula</button>
</form>

<h2>Próximas aulas · enviar</h2>{corpo}
</body></html>"""