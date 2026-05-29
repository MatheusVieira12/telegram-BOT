import os
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! 👋\n\n"
        "Envie um gasto assim:\n"
        "ifood 45\n"
        "uber 32\n\n"
        "Comandos:\n"
        "/gastos\n"
        "/excel\n"
        "/corrigir palavra categoria"
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
        f"Descrição: {gasto['descricao']}\n"
        f"Valor: R$ {gasto['valor']:.2f}\n"
        f"Categoria: {gasto['categoria']}\n"
        f"Data: {gasto['data']}"
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
        texto += f"#{g.id} - {g.descricao} | R$ {g.valor:.2f} | {g.categoria} | {g.data}\n"

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


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("gastos", listar_gastos))
telegram_app.add_handler(CommandHandler("excel", enviar_excel))
telegram_app.add_handler(CommandHandler("corrigir", corrigir_categoria))
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