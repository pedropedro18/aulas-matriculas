from datetime import timedelta
from sqlalchemy import select
from .db import Session, Aula, Aluno, agora
from .whatsapp import enviar


def _avisar(db, aula: Aula, quando: str):
    alunos = db.scalars(
        select(Aluno).where(Aluno.nivel == aula.nivel, Aluno.pago == True)  # noqa: E712
    ).all()
    for a in alunos:
        enviar(
            a.telefone,
            f"📚 Lembrete: aula de {aula.nivel} {quando} "
            f"({aula.inicio:%d/%m às %H:%M}).\n{aula.link}",
        )


def verificar_lembretes():
    """Corre a cada minuto."""
    with Session() as db:
        agora_ = agora()
        for aula in db.scalars(select(Aula).where(Aula.inicio > agora_)).all():
            falta = aula.inicio - agora_
            if not aula.lembrete_24h and falta <= timedelta(hours=24):
                _avisar(db, aula, "amanhã")
                aula.lembrete_24h = True
            if not aula.lembrete_1h and falta <= timedelta(hours=1):
                _avisar(db, aula, "daqui a 1 hora")
                aula.lembrete_1h = True
        db.commit()