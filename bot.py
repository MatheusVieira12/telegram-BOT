import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from sqlalchemy import func

from database import Session, Gasto, CategoriaPersonalizada
from parser import processar_mensagem
from export_excel import exportar_excel

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN não configurado.")

app = FastAPI()
telegram_app = ApplicationBuilder().token(TOKEN).build()


def mes_atual():
    return datetime.now().strftime("%Y-%m")


def formatar_moeda(valor):
    return f"R$ {valor:.2f}".replace(".", ",")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! 👋\n\n"
        "Envie um gasto assim:\n"
        "ifood 45\n"
        "uber 32\n\n"
        "Comandos:\n"
        "/gastos - últimos gastos\n"
        "/resumo - resumo do mês\n"
        "/ranking - ranking por categoria\n"
        "/excel - baixar planilha\n"
        "/corrigir palavra categoria - ensinar categoria\n"
        "/deletar ID - apagar um gasto"
    )


async def registrar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    gasto = processar_mensagem(texto)

    if not gasto:
        await update.message.reply_text("Não entendi. Envie algo como: ifood 45")
        return

    session = Session()

    novo = Gasto(
        descricao=gasto["descricao"],
        valor=gasto["valor"],
        categoria=gasto["categoria"],
        data=gasto["data"]
    )

    session.add(novo)
    session.commit()
    session.close()

    await update.message.reply_text(
        "✅ Gasto registrado!\n\n"
        f"📝 Descrição: {gasto['descricao']}\n"
        f"💰 Valor: {formatar_moeda(gasto['valor'])}\n"
        f"🏷 Categoria: {gasto['categoria']}\n"
        f"📅 Data: {gasto['data']}"
    )


async def listar_gastos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()

    gastos = (
        session.query(Gasto)
        .order_by(Gasto.id.desc())
        .limit(10)
        .all()
    )

    session.close()

    if not gastos:
        await update.message.reply_text("Nenhum gasto registrado ainda.")
        return

    texto = "📋 Últimos gastos:\n\n"

    for g in gastos:
        texto += (
            f"#{g.id} - {g.descricao}\n"
            f"{formatar_moeda(g.valor)} | {g.categoria} | {g.data}\n\n"
        )

    await update.message.reply_text(texto)


async def enviar_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caminho = exportar_excel()

    with open(caminho, "rb") as arquivo:
        await update.message.reply_document(
            document=arquivo,
            filename="gastos.xlsx",
            caption="📊 Sua planilha de gastos"
        )


async def corrigir_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Use assim:\n/corrigir palavra categoria")
        return

    palavra = context.args[0].lower()
    categoria = context.args[1].lower()

    session = Session()

    existente = (
        session.query(CategoriaPersonalizada)
        .filter_by(palavra=palavra)
        .first()
    )

    if existente:
        existente.categoria = categoria
    else:
        session.add(CategoriaPersonalizada(palavra=palavra, categoria=categoria))

    session.commit()
    session.close()

    await update.message.reply_text(
        f"✅ Aprendi!\nSempre que eu ver '{palavra}', vou usar '{categoria}'."
    )


async def resumo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    mes = mes_atual()

    gastos = (
        session.query(Gasto)
        .filter(Gasto.data.like(f"{mes}%"))
        .all()
    )

    if not gastos:
        session.close()
        await update.message.reply_text("Você ainda não tem gastos registrados neste mês.")
        return

    total = sum(g.valor for g in gastos)
    quantidade = len(gastos)
    media = total / quantidade if quantidade else 0

    por_categoria = {}

    for g in gastos:
        por_categoria[g.categoria] = por_categoria.get(g.categoria, 0) + g.valor

    maior_categoria = max(por_categoria, key=por_categoria.get)
    maior_valor = por_categoria[maior_categoria]

    texto = "📊 Resumo do mês\n\n"
    texto += f"💰 Total gasto: {formatar_moeda(total)}\n"
    texto += f"🧾 Quantidade de gastos: {quantidade}\n"
    texto += f"📈 Média por gasto: {formatar_moeda(media)}\n\n"

    texto += "🏷 Gastos por categoria:\n"

    for categoria, valor in sorted(por_categoria.items(), key=lambda x: x[1], reverse=True):
        percentual = (valor / total) * 100
        texto += f"• {categoria}: {formatar_moeda(valor)} ({percentual:.1f}%)\n"

    texto += f"\n🥇 Maior categoria: {maior_categoria} — {formatar_moeda(maior_valor)}"

    session.close()

    await update.message.reply_text(texto)


async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    mes = mes_atual()

    resultados = (
        session.query(
            Gasto.categoria,
            func.sum(Gasto.valor).label("total")
        )
        .filter(Gasto.data.like(f"{mes}%"))
        .group_by(Gasto.categoria)
        .order_by(func.sum(Gasto.valor).desc())
        .all()
    )

    session.close()

    if not resultados:
        await update.message.reply_text("Nenhum gasto encontrado para este mês.")
        return

    medalhas = ["🥇", "🥈", "🥉"]
    total_geral = sum(r.total for r in resultados)

    texto = "🏆 Ranking de categorias do mês\n\n"

    for i, r in enumerate(resultados):
        posicao = medalhas[i] if i < 3 else f"{i + 1}º"
        percentual = (r.total / total_geral) * 100 if total_geral else 0
        texto += f"{posicao} {r.categoria}: {formatar_moeda(r.total)} ({percentual:.1f}%)\n"

    texto += f"\n💰 Total: {formatar_moeda(total_geral)}"

    await update.message.reply_text(texto)


async def deletar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(
            "Use:\n/deletar ID\n\nExemplo:\n/deletar 15"
        )
        return

    try:
        gasto_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ O ID precisa ser um número.")
        return

    session = Session()

    gasto = (
        session.query(Gasto)
        .filter_by(id=gasto_id)
        .first()
    )

    if not gasto:
        session.close()
        await update.message.reply_text(
            f"❌ Gasto #{gasto_id} não encontrado."
        )
        return

    descricao = gasto.descricao
    valor = gasto.valor
    categoria = gasto.categoria
    data = gasto.data

    session.delete(gasto)
    session.commit()
    session.close()

    await update.message.reply_text(
        "🗑 Gasto removido com sucesso!\n\n"
        f"🆔 ID: #{gasto_id}\n"
        f"📝 Descrição: {descricao}\n"
        f"💰 Valor: {formatar_moeda(valor)}\n"
        f"🏷 Categoria: {categoria}\n"
        f"📅 Data: {data}"
    )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("gastos", listar_gastos))
telegram_app.add_handler(CommandHandler("excel", enviar_excel))
telegram_app.add_handler(CommandHandler("corrigir", corrigir_categoria))
telegram_app.add_handler(CommandHandler("resumo", resumo))
telegram_app.add_handler(CommandHandler("ranking", ranking))
telegram_app.add_handler(CommandHandler("deletar", deletar_gasto))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registrar_gasto))


@app.on_event("startup")
async def startup():
    await telegram_app.initialize()

    if WEBHOOK_URL:
        webhook_url = WEBHOOK_URL.strip().rstrip("/") + "/webhook"
        print(f"Configurando webhook em: {webhook_url}", flush=True)

        try:
            await telegram_app.bot.set_webhook(url=webhook_url)
            print("Webhook configurado com sucesso!", flush=True)
        except Exception as e:
            print(f"Erro ao configurar webhook: {e}", flush=True)

    await telegram_app.start()


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.get("/")
def home():
    return {"status": "bot online"}


@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}