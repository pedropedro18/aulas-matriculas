from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, Response, HTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.config import VERIFY_TOKEN, ADMIN_NUMBER, PRECO_KZ, IBAN, NIVEIS
from app.db import Session, Aluno, Pagamento, Aula, criar_tabelas
from app.lembretes import verificar_lembretes
from whatsapp import enviar


@asynccontextmanager
async def lifespan(app: FastAPI):
    criar_tabelas()
    sched = BackgroundScheduler(timezone="Africa/Luanda")
    sched.add_job(verificar_lembretes, "interval", minutes=1)
    sched.start()
    yield
    sched.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def raiz():
    return {"status": "online"}


@app.get("/webhook")
def verificar(request: Request):
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(p.get("hub.challenge"), media_type="text/plain")
    raise HTTPException(403)


@app.post("/webhook")
async def receber(request: Request):
    dados = await request.json()
    try:
        msg = dados["entry"][0]["changes"][0]["value"]["messages"][0]
    except (KeyError, IndexError):
        return {"ok": True}  # notificações de estado, ignorar
    tel = msg["from"]
    tipo = msg["type"]
    texto = msg.get("text", {}).get("body", "").strip()
    with Session() as db:
        tratar(db, tel, texto, tipo)
    return {"ok": True}


def tratar(db, tel: str, texto: str, tipo: str):
    if tel == ADMIN_NUMBER and texto.startswith("/"):
        return comando_admin(db, texto)

    aluno = db.scalar(select(Aluno).where(Aluno.telefone == tel))
    if not aluno:
        db.add(Aluno(telefone=tel))
        db.commit()
        return enviar(tel, "Olá! 👋 Sou o assistente do Teacher Pedro.\nQual é o teu nome completo?")

    if aluno.estado == "nome":
        aluno.nome = texto.title()
        aluno.estado = "nivel"
        db.commit()
        return enviar(tel, f"Prazer, {aluno.nome}! Qual é o teu nível? ({', '.join(NIVEIS)})")

    if aluno.estado == "nivel":
        nivel = texto.upper()
        if nivel not in NIVEIS:
            return enviar(tel, f"Nível inválido. Escolhe: {', '.join(NIVEIS)}")
        aluno.nivel = nivel
        aluno.estado = "aguarda_pagamento"
        pag = Pagamento(aluno_id=aluno.id, valor=PRECO_KZ)
        db.add(pag)
        db.commit()
        return enviar(
            tel,
            f"Matrícula {nivel}: {PRECO_KZ} Kz.\nTransfere para o IBAN {IBAN} "
            f"(referência: PAG{pag.id}) e envia aqui o comprovativo (foto ou PDF).",
        )

    if aluno.estado == "aguarda_pagamento":
        if tipo in ("image", "document"):
            pag = db.scalar(
                select(Pagamento)
                .where(Pagamento.aluno_id == aluno.id, Pagamento.estado == "pendente")
                .order_by(Pagamento.id.desc())
            )
            if not pag:
                return enviar(tel, "Não encontrei pagamento pendente. Fala com o Teacher Pedro.")
            enviar(ADMIN_NUMBER, f"💰 Comprovativo de {aluno.nome} ({aluno.nivel}), "
                                 f"pagamento #{pag.id}. Responde /confirmar {pag.id}")
            return enviar(tel, "Recebido! Vamos confirmar o pagamento em breve. ✅")
        return enviar(tel, "Estou à espera do comprovativo (foto ou PDF).")

    # estado "ativo"
    return enviar(tel, "Estás matriculado ✅ Vais receber lembretes antes de cada aula.")


def comando_admin(db, texto: str):
    partes = texto.split()
    cmd = partes[0]
    try:
        if cmd == "/confirmar":
            pag = db.get(Pagamento, int(partes[1]))
            pag.estado = "confirmado"
            aluno = db.get(Aluno, pag.aluno_id)
            aluno.pago, aluno.estado = True, "ativo"
            db.commit()
            enviar(aluno.telefone, "Pagamento confirmado! 🎉 Bem-vindo(a) às aulas.")
            return enviar(ADMIN_NUMBER, f"Confirmado: {aluno.nome}")
        if cmd == "/aula":  # /aula B1 2026-10-25 18:00 https://meet...
            inicio = datetime.strptime(f"{partes[2]} {partes[3]}", "%Y-%m-%d %H:%M")
            db.add(Aula(nivel=partes[1].upper(), inicio=inicio,
                        link=partes[4] if len(partes) > 4 else ""))
            db.commit()
            return enviar(ADMIN_NUMBER, "Aula agendada ✅")
    except (IndexError, ValueError, AttributeError):
        pass
    enviar(ADMIN_NUMBER, "Comandos:\n/confirmar <id>\n/aula <nível> AAAA-MM-DD HH:MM <link>")