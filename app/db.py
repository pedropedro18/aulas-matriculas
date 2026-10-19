from datetime import datetime
from zoneinfo import ZoneInfo
import certifi
from sqlalchemy import create_engine, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATABASE_URL, USA_MYSQL

if USA_MYSQL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"ssl": {"ca": certifi.where()}},
        pool_pre_ping=True,
        pool_recycle=300,
    )
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

Session = sessionmaker(engine, expire_on_commit=False)


def agora() -> datetime:
    """Hora local de Angola, sem fuso (guardamos tudo em hora local)."""
    return datetime.now(ZoneInfo("Africa/Luanda")).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Aluno(Base):
    __tablename__ = "alunos"
    id: Mapped[int] = mapped_column(primary_key=True)
    telefone: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str | None] = mapped_column(String(100))
    nivel: Mapped[str | None] = mapped_column(String(2))
    estado: Mapped[str] = mapped_column(String(30), default="nome")
    pago: Mapped[bool] = mapped_column(default=False)


class Pagamento(Base):
    __tablename__ = "pagamentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"))
    valor: Mapped[int]
    estado: Mapped[str] = mapped_column(String(20), default="pendente")
    criado_em: Mapped[datetime] = mapped_column(default=agora)


class Aula(Base):
    __tablename__ = "aulas"
    id: Mapped[int] = mapped_column(primary_key=True)
    nivel: Mapped[str] = mapped_column(String(2))
    inicio: Mapped[datetime]
    link: Mapped[str] = mapped_column(String(500), default="")
    lembrete_24h: Mapped[bool] = mapped_column(default=False)
    lembrete_1h: Mapped[bool] = mapped_column(default=False)


def criar_tabelas():
    Base.metadata.create_all(engine)