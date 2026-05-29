import os
import pandas as pd
from database import Session, Gasto


def exportar_excel():
    os.makedirs("exports", exist_ok=True)

    session = Session()
    gastos = session.query(Gasto).all()

    dados = []

    for g in gastos:
        dados.append({
            "ID": g.id,
            "Descrição": g.descricao,
            "Valor": g.valor,
            "Categoria": g.categoria,
            "Data": g.data
        })

    session.close()

    caminho = "exports/gastos.xlsx"

    df = pd.DataFrame(dados)
    df.to_excel(caminho, index=False)

    return caminho