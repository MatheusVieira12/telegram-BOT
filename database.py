from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import os

os.makedirs("data", exist_ok=True)

engine = create_engine("sqlite:///data/gastos.db")

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