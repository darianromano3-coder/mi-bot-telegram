import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ===== CONFIG GRUPO =====
ID_GRUPO = -1001887048480
LINK_GRUPO = "https://t.me/Hc_Drill"

logging.basicConfig(level=logging.INFO)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "users.json")

PLANES = {
    "7": {"dias": 7, "precio": "$1000"},
    "15": {"dias": 15, "precio": "$1800"},
    "30": {"dias": 30, "precio": "$3000"},
    "perma": {"dias": 9999, "precio": "$5000"}
}

user_states = {}
pending_payments = {}

# ================= DATA =================

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "admins": [],
            "users": {},
            "free_uses": {},
            "referrals": {},
            "invited_by": {}
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return data

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    for key in ["free_uses", "referrals", "invited_by"]:
        if key not in data:
            data[key] = {}

    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ================= SEGURIDAD =================

def is_admin(user_id):
    data = load_data()
    return int(user_id) in [int(x) for x in data["admins"]]


def is_allowed(user_id):
    data = load_data()
    if str(user_id) in data["users"]:
        expire = datetime.fromisoformat(data["users"][str(user_id)])
        return datetime.now() < expire
    return False


def check_free_trial(user_id):
    data = load_data()
    uid = str(user_id)

    if uid not in data["free_uses"]:
        data["free_uses"][uid] = 5

    if data["free_uses"][uid] > 0:
        data["free_uses"][uid] -= 1
        save_data(data)
        return True, data["free_uses"][uid]

    return False, 0


# ================= GRUPO =================

async def esta_en_grupo(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=ID_GRUPO, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


def teclado_grupo():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Unirme al grupo", url=LINK_GRUPO)],
        [InlineKeyboardButton("✅ Ya me uní", callback_data="check_group")]
    ])


# ================= SSH =================

def dec_ssh(ld):
    try:
        userlv = ld.split('.')[::2]
        userld = ld.split('.')[1::2]
        newld = ""
        for x in range(len(userld)):
            v = int(userlv[x]) - len(userlv)
            w = int(userld[x]) - len(userlv)
            m = (v // (2 ** w)) % 256
            newld += chr(m)
        return newld
    except:
        return "Error"


# ================= COMANDOS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    data = load_data()

    if len(data["admins"]) == 0:
        data["admins"].append(user.id)
        save_data(data)
        await update.message.reply_text("👑 Te asigné como ADMIN automáticamente")

    # REFERIDOS
    if context.args:
        inviter_id = context.args[0]

        if inviter_id != user_id and user_id not in data["invited_by"]:
            data["invited_by"][user_id] = inviter_id

            if inviter_id not in data["referrals"]:
                data["referrals"][inviter_id] = 0

            data["referrals"][inviter_id] += 1

            if data["referrals"][inviter_id] % 2 == 0:
                if inviter_id in data["users"]:
                    expire = datetime.fromisoformat(data["users"][inviter_id])
                else:
                    expire = datetime.now()

                new_expire = expire + timedelta(days=1)
                data["users"][inviter_id] = new_expire.isoformat()

                try:
                    await context.bot.send_message(
                        inviter_id,
                        "🎉 Invitaste 2 usuarios y ganaste 1 día gratis!"
                    )
                except:
                    pass

            save_data(data)

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"

    await update.message.reply_text(
        f"🤖 Bot activo\n\n"
        f"🔗 Tu link:\n{link}\n\n"
        f"🎁 Invita 2 = 1 día gratis"
    )


async def refs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    total = data["referrals"].get(user_id, 0)
    faltan = 2 - (total % 2)

    await update.message.reply_text(
        f"👥 Referidos: {total}\n"
        f"📊 Te faltan {faltan} para 1 día gratis"
    )


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Tu ID: {update.effective_user.id}")


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📅 7 días - $1000", callback_data="plan_7")],
        [InlineKeyboardButton("📅 15 días - $1800", callback_data="plan_15")],
        [InlineKeyboardButton("📅 30 días - $3000", callback_data="plan_30")],
        [InlineKeyboardButton("♾ Permanente - $5000", callback_data="plan_perma")]
    ]

    await update.message.reply_text(
        "💳 Selecciona un plan:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= PLANES =================

async def plan_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_id = query.data.split("_")[1]
    plan = PLANES.get(plan_id)

    if not plan:
        return

    texto = f"""
💳 PLAN SELECCIONADO

📅 Duración: {plan['dias']} días
💰 Precio: {plan['precio']}

📌 PASOS:
1️⃣ Realizar pago
2️⃣ Enviar comprobante
3️⃣ Esperar verificación

👤 Admin: @Giovani2k
"""

    keyboard = [
        [InlineKeyboardButton("📤 Enviar comprobante", callback_data=f"send_{plan_id}")],
        [InlineKeyboardButton("📩 Contactar Admin", url="https://t.me/Giovani2k")],
        [InlineKeyboardButton("🔙 Volver", callback_data="back_buy")]
    ]

    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))


# ================= SSH =================

async def ssh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await esta_en_grupo(context.bot, user_id):
        await update.message.reply_text(
            "🚫 Debes unirte al grupo",
            reply_markup=teclado_grupo()
        )
        return

    if not is_allowed(user_id):
        ok, remaining = check_free_trial(user_id)
        if not ok:
            await update.message.reply_text("❌ Sin acceso\nUsa /buy")
            return
        else:
            await update.message.reply_text(f"🎁 Te quedan {remaining} usos")

    try:
        data = " ".join(context.args)

        server = data.split('@')[0].split(':')[0]
        port = data.split('@')[0].split(':')[1]

        user = dec_ssh(data.split('@')[1].split(':')[0])
        password = dec_ssh(data.split('@')[1].split(':')[1])

        await update.message.reply_text(
            f"🔐 SSH\n🌐 {server}\n🔌 {port}\n👤 {user}\n🔑 {password}"
        )
    except:
        await update.message.reply_text("❌ Error formato")


# ================= ADMIN =================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ No eres admin")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Agregar Usuario", callback_data="add_user")],
        [InlineKeyboardButton("✏️ Editar Usuario", callback_data="edit_user")],
        [InlineKeyboardButton("➖ Eliminar Usuario", callback_data="remove_user")],
        [InlineKeyboardButton("👑 Agregar Admin", callback_data="add_admin")],
        [InlineKeyboardButton("📊 Ver Usuarios", callback_data="view_users")]
    ]

    await update.message.reply_text("👑 PANEL ADMIN", reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "check_group":
        if await esta_en_grupo(context.bot, user_id):
            await query.edit_message_text("✅ Verificado, ya puedes usar el bot")
        else:
            await query.answer("Aún no te uniste", show_alert=True)
        return

    if query.data.startswith("plan_"):
        await plan_info(update, context)
        return

    if query.data == "back_buy":
        await buy(update, context)
        return

    if query.data.startswith("send_"):
        plan_id = query.data.split("_")[1]
        user_states[user_id] = f"waiting_proof_{plan_id}"
        await query.edit_message_text("📤 Envía comprobante (imagen o texto)")
        return

    if query.data.startswith("approve_"):
        uid = query.data.split("_")[1]
        info = pending_payments.get(uid)

        if info:
            dias = PLANES[info["plan"]]["dias"]
            data = load_data()
            expire = datetime.now() + timedelta(days=dias)
            data["users"][uid] = expire.isoformat()
            save_data(data)

            await context.bot.send_message(uid, "✅ Pago aprobado")
            del pending_payments[uid]

        await query.edit_message_text("✅ Aprobado")
        return

    if query.data.startswith("reject_"):
        uid = query.data.split("_")[1]

        if uid in pending_payments:
            del pending_payments[uid]

        await context.bot.send_message(uid, "❌ Pago rechazado")
        await query.edit_message_text("❌ Rechazado")
        return

    if not is_admin(user_id):
        return

    if query.data == "add_user":
        user_states[user_id] = "add_id"
        await query.edit_message_text("ID usuario")

    elif query.data == "edit_user":
        user_states[user_id] = "edit_id"
        await query.edit_message_text("ID usuario")

    elif query.data == "remove_user":
        user_states[user_id] = "remove_id"
        await query.edit_message_text("ID usuario")

    elif query.data == "add_admin":
        user_states[user_id] = "admin_id"
        await query.edit_message_text("Nuevo admin ID")

    elif query.data == "view_users":
        data = load_data()
        text = "Usuarios:\n"
        for uid, exp in data["users"].items():
            dias = (datetime.fromisoformat(exp) - datetime.now()).days
            text += f"{uid} → {dias} días\n"
        await query.edit_message_text(text)


async def admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    data = load_data()

    if str(user_states.get(user_id, "")).startswith("waiting_proof_"):
        plan_id = user_states[user_id].split("_")[2]
        pending_payments[str(user_id)] = {"plan": plan_id}

        for admin in data["admins"]:
            keyboard = [[
                InlineKeyboardButton("✅ Aprobar", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"reject_{user_id}")
            ]]
            await context.bot.send_message(
                admin,
                f"💳 Pago nuevo\nUsuario: {user_id}\nPlan: {plan_id}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        await update.message.reply_text("📨 Enviado. Esperando verificación")
        user_states.pop(user_id)
        return

    if user_id not in user_states:
        return

    try:
        if user_states[user_id] == "add_id":
            context.user_data["uid"] = text
            user_states[user_id] = "add_days"
            await update.message.reply_text("Días")

        elif user_states[user_id] == "add_days":
            uid = context.user_data["uid"]
            dias = int(text)
            expire = datetime.now() + timedelta(days=dias)
            data["users"][uid] = expire.isoformat()
            save_data(data)
            await update.message.reply_text("Usuario agregado")
            user_states.pop(user_id)

        elif user_states[user_id] == "edit_id":
            context.user_data["uid"] = text
            user_states[user_id] = "edit_days"
            await update.message.reply_text("Nuevos días")

        elif user_states[user_id] == "edit_days":
            uid = context.user_data["uid"]
            dias = int(text)
            expire = datetime.now() + timedelta(days=dias)
            data["users"][uid] = expire.isoformat()
            save_data(data)
            await update.message.reply_text("Actualizado")
            user_states.pop(user_id)

        elif user_states[user_id] == "remove_id":
            if text in data["users"]:
                del data["users"][text]
                save_data(data)
                await update.message.reply_text("Eliminado")
            else:
                await update.message.reply_text("No existe")
            user_states.pop(user_id)

        elif user_states[user_id] == "admin_id":
            new_admin = int(text)
            if new_admin not in data["admins"]:
                data["admins"].append(new_admin)
                save_data(data)
                await update.message.reply_text("Admin agregado")
            else:
                await update.message.reply_text("Ya es admin")
            user_states.pop(user_id)

    except:
        await update.message.reply_text("Error")
        user_states.pop(user_id)


# ================= JOB =================

async def check_expirations(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    now = datetime.now()

    for uid, exp in list(data["users"].items()):
        if datetime.fromisoformat(exp) <= now:
            try:
                await context.bot.send_message(uid, "❌ Expirado")
            except:
                pass
            del data["users"][uid]

    save_data(data)


# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("ssh", ssh))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("refs", refs))

    app.add_handler(CallbackQueryHandler(admin_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_messages))

    app.job_queue.run_repeating(check_expirations, interval=86400, first=10)
    import threading
from flask import Flask
import os

flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Bot activo ✅"

def run_server():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

# Iniciar servidor en segundo plano
threading.Thread(target=run_server, daemon=True).start()

    print("🔥 BOT FUNCIONANDO")
    app.run_polling()


if __name__ == "__main__":
    main()
