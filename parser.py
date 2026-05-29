import re
from datetime import datetime
from database import Session, CategoriaPersonalizada

CATEGORIAS = {
    "alimentacao": [
        "ifood", "mercado", "restaurante", "lanche", "pizza",
        "hamburguer", "padaria", "mcdonalds", "bk", "comida"
    ],
    "transporte": [
        "uber", "99", "onibus", "ônibus", "metro", "metrô",
        "gasolina", "posto", "estacionamento"
    ],
    "moradia": [
        "aluguel", "condominio", "condomínio", "luz",
        "agua", "água", "internet"
    ],
    "saude": [
        "farmacia", "farmácia", "remedio", "remédio",
        "consulta", "exame"
    ],
    "assinatura": [
        "netflix", "spotify", "prime", "disney", "youtube"
    ],
    "lazer": [
        "cinema", "bar", "show", "festa"
    ],
    "educacao": [
        "curso", "faculdade", "livro", "udemy"
    ]
}


def detectar_categoria(texto):
    texto = texto.lower()

    session = Session()
    categorias_custom = session.query(CategoriaPersonalizada).all()
    session.close()

    for item in categorias_custom:
        if item.palavra.lower() in texto:
            return item.categoria

    for categoria, palavras in CATEGORIAS.items():
        for palavra in palavras:
            if palavra in texto:
                return categoria

    return "geral"


def processar_mensagem(texto):
    texto = texto.lower().strip()

    valor_encontrado = re.search(r"\d+([.,]\d+)?", texto)

    if not valor_encontrado:
        return None

    valor = float(valor_encontrado.group().replace(",", "."))

    texto_sem_valor = texto.replace(valor_encontrado.group(), "").strip()

    descricao = texto_sem_valor if texto_sem_valor else "gasto"

    categoria = detectar_categoria(texto)

    return {
        "descricao": descricao,
        "valor": valor,
        "categoria": categoria,
        "data": datetime.now().strftime("%Y-%m-%d")
    }