import os
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

# fallback local, caso você rode no PC sem DATABASE_URL
if not DATABASE_URL:
    os.makedirs("data", exist_ok=True)
    DATABASE_URL = "sqlite:///data/gastos.db"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

Base = declarative_base()


class Gasto(Base):
    __tablename__ = "gastos"

    id = Column(Integer, primary_key=True)
    descricao = Column(String)
    valor = Column(Float)
    categoria = Column(String)
    data = Column(String)


class CategoriaPersonalizada(Base):
    __tablename__ = "categorias_personalizadas"

    id = Column(Integer, primary_key=True)
    palavra = Column(String, unique=True)
    categoria = Column(String)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)