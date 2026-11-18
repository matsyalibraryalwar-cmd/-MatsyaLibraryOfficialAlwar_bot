import os, sqlite3, logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
DB = os.getenv("DB_PATH", "matsya_library.db")

NAME, PHONE, PLAN, SEAT, COMPLAINT = range(5)
PLANS = {
    "Full Day": ("₹600/month", "06:00 AM – 09:00 PM"),
    "Half Day Morning": ("₹400/month", "06:00 AM – 02:00 PM"),
    "Half Day Evening": ("₹400/month", "02:00 PM – 09:00 PM"),
}
MAIN_KEYS = [
    ["📝 Online Admission", "💺 Seat Information"],
    ["💰 Fee Plans", "📋 My Details"],
    ["🛠️ Submit Complaint", "📍 Location & Contact"],
    ["📖 Library Rules", "☎️ Contact Admin"],
]
def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS students(
        tg_id INTEGER PRIMARY KEY, username TEXT, name TEXT, phone TEXT, plan TEXT,
        seat TEXT DEFAULT '', status TEXT DEFAULT 'Pending', fee_status TEXT DEFAULT 'Pending',
        created_at TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS complaints(
        id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER, name TEXT, category TEXT,
        detail TEXT, status TEXT DEFAULT 'Open', created_at TEXT)""")
    con.commit()
    return con

def is_admin(uid): return uid in ADMIN_IDS
def menu(): return ReplyKeyboardMarkup(MAIN_KEYS, resize_keyboard=True)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"नमस्कार {user.first_name}! 🌿\n\n*Matsya Library Alwar* में आपका स्वागत है।\n\n"
        "यहाँ से आप ऑनलाइन एडमिशन, सीट जानकारी, फीस प्लान और शिकायत दर्ज कर सकते हैं।",
        parse_mode="Markdown", reply_markup=menu())
    return ConversationHandler.END

async def admission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ऑनलाइन एडमिशन के लिए अपना पूरा नाम लिखें:")
    return NAME
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("अपना मोबाइल नंबर साझा करने के लिए नीचे बटन दबाएँ या नंबर टाइप करें:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📱 मोबाइल नंबर साझा करें", request_contact=True)], ["❌ रद्द करें"]], resize_keyboard=True))
    return PHONE
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number if update.message.contact else update.message.text.strip()
    if phone == "❌ रद्द करें": return await cancel(update, context)
    context.user_data["phone"] = phone
    kb = [[InlineKeyboardButton(f"{p} — {v[0]}", callback_data=f"plan:{p}")] for p,v in PLANS.items()]
    await update.message.reply_text("अपना Membership Plan चुनें:", reply_markup=InlineKeyboardMarkup(kb))
    return PLAN
async def get_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    plan = q.data.split(":",1)[1]
    context.user_data["plan"] = plan
    con = db()
    con.execute("""INSERT INTO students(tg_id,username,name,phone,plan,created_at)
      VALUES(?,?,?,?,?,?) ON CONFLICT(tg_id) DO UPDATE SET username=excluded.username,
      name=excluded.name,phone=excluded.phone,plan=excluded.plan,status='Pending'""",
      (q.from_user.id, q.from_user.username or "", context.user_data["name"], context.user_data["phone"], plan, datetime.now().isoformat(timespec="minutes")))
    con.commit(); con.close()
    await q.edit_message_text(f"आपका आवेदन प्राप्त हुआ।\n\nनाम: {context.user_data['name']}\nमोबाइल: {context.user_data['phone']}\nप्लान: {plan}\n\nस्थिति: Pending Approval\nAdmin द्वारा पुष्टि के बाद आपको सूचना दी जाएगी।")
    for aid in ADMIN_IDS:
        try: await context.bot.send_message(aid, f"🆕 नया Admission Request\nनाम: {context.user_data['name']}\nफोन: {context.user_data['phone']}\nप्लान: {plan}\nTelegram ID: {q.from_user.id}\nस्वीकृत करने के लिए: /approve {q.from_user.id}")
        except Exception: pass
    await q.message.reply_text("मुख्य मेन्यू:", reply_markup=menu())
    return ConversationHandler.END

async def complaint_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["💺 Seat/Chair", "🚰 Water/Washroom"], ["💡 Light/Fan", "📶 Wi-Fi/Internet"], ["🧹 Cleanliness", "अन्य"], ["❌ रद्द करें"]]
    await update.message.reply_text("शिकायत की श्रेणी चुनें:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return COMPLAINT
async def complaint_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ रद्द करें": return await cancel(update, context)
    context.user_data["complaint_category"] = update.message.text
    await update.message.reply_text("कृपया समस्या का पूरा विवरण लिखें:")
    return SEAT
async def complaint_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con=db()
    s=con.execute("SELECT name FROM students WHERE tg_id=?",(update.effective_user.id,)).fetchone()
    name=s["name"] if s else update.effective_user.full_name
    cur=con.execute("INSERT INTO complaints(tg_id,name,category,detail,created_at) VALUES(?,?,?,?,?)",
      (update.effective_user.id,name,context.user_data.get("complaint_category","Other"),update.message.text,datetime.now().isoformat(timespec="minutes")))
    cid=cur.lastrowid; con.commit(); con.close()
    await update.message.reply_text(f"आपकी शिकायत दर्ज हो गई है। शिकायत क्रमांक: #{cid}", reply_markup=menu())
    for aid in ADMIN_IDS:
        try: await context.bot.send_message(aid,f"🛠️ नई शिकायत #{cid}\nनाम: {name}\nश्रेणी: {context.user_data.get('complaint_category')}\nविवरण: {update.message.text}\nTelegram ID: {update.effective_user.id}")
        except Exception: pass
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("प्रक्रिया रद्द कर दी गई।", reply_markup=menu())
    return ConversationHandler.END

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t=update.message.text
    if t=="📝 Online Admission": return await admission(update,context)
    if t=="🛠️ Submit Complaint": return await complaint_start(update,context)
    if t=="💺 Seat Information":
        con=db(); count=con.execute("SELECT COUNT(*) n FROM students WHERE status='Approved'").fetchone()["n"]; con.close()
        await update.message.reply_text(f"कुल क्षमता: 120 सीटें\nस्वीकृत विद्यार्थी: {count}\nउपलब्ध सीटें (अनुमानित): {max(0,120-count)}\nअंतिम सीट पुष्टि Admin से करें।",reply_markup=menu())
    elif t=="💰 Fee Plans":
        await update.message.reply_text("Membership Plans:\n\nFull Day: ₹600/month\nसमय: 06:00 AM – 09:00 PM\n\nHalf Day Morning: ₹400/month\nसमय: 06:00 AM – 02:00 PM\n\nHalf Day Evening: ₹400/month\nसमय: 02:00 PM – 09:00 PM\n\nRegistration: ₹0",reply_markup=menu())
    elif t=="📋 My Details":
        con=db(); s=con.execute("SELECT * FROM students WHERE tg_id=?",(update.effective_user.id,)).fetchone(); con.close()
        if s: msg=f"आपकी जानकारी:\nनाम: {s['name']}\nमोबाइल: {s['phone']}\nप्लान: {s['plan']}\nसीट: {s['seat'] or 'अभी आवंटित नहीं'}\nAdmission: {s['status']}\nFee: {s['fee_status']}"
        else: msg="आपका रिकॉर्ड नहीं मिला। एडमिशन के लिए Online Admission चुनें।"
        await update.message.reply_text(msg,reply_markup=menu())
    elif t=="📍 Location & Contact":
        await update.message.reply_text("Matsya Library Alwar\nपता: B7, Malviya Nagar, Alwar, Rajasthan – 301001\nOfficial Contact: 9950394045\nSecondary Contact: 9660920057",reply_markup=menu())
    elif t=="📖 Library Rules":
        await update.message.reply_text("📖 Library Rules\n1. सदस्यता व्यक्तिगत है।\n2. शांत एवं अनुशासित वातावरण बनाए रखें।\n3. सीट और समय का पालन करें।\n4. स्वच्छता बनाए रखें।\n5. किसी भी समस्या के लिए Bot पर शिकायत दर्ज करें।",reply_markup=menu())
    elif t=="☎️ Contact Admin":
        await update.message.reply_text("सहायता के लिए Matsya Library Alwar के Official Contact 9950394045 पर संपर्क करें।",reply_markup=menu())
    else:
        await update.message.reply_text("कृपया नीचे दिए गए मेन्यू से विकल्प चुनें।",reply_markup=menu())

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return await update.message.reply_text("यह कमांड केवल Admin के लिए है।")
    await update.message.reply_text("🔐 Admin Commands:\n/students – विद्यार्थी सूची\n/complaints – शिकायत सूची\n/seats – सीट स्थिति\n/approve TELEGRAM_ID – Admission approve\n/fee TELEGRAM_ID paid – फीस Paid करें\n/assign TELEGRAM_ID SEAT – सीट आवंटित करें\n/broadcast संदेश – सभी विद्यार्थियों को संदेश")

async def students(update,context):
    if not is_admin(update.effective_user.id): return
    con=db(); rows=con.execute("SELECT tg_id,name,phone,plan,status,seat FROM students ORDER BY created_at DESC LIMIT 50").fetchall(); con.close()
    if not rows: return await update.message.reply_text("अभी कोई विद्यार्थी नहीं है।")
    msg="विद्यार्थी (अधिकतम 50):\n"+"\n".join([f"{r['name']} | {r['phone']} | {r['plan']} | {r['status']} | Seat:{r['seat'] or '-'} | ID:{r['tg_id']}" for r in rows])
    await update.message.reply_text(msg)
async def complaints(update,context):
    if not is_admin(update.effective_user.id): return
    con=db(); rows=con.execute("SELECT * FROM complaints ORDER BY id DESC LIMIT 30").fetchall(); con.close()
    if not rows: return await update.message.reply_text("कोई शिकायत नहीं।")
    await update.message.reply_text("\n\n".join([f"#{r['id']} {r['name']} | {r['category']} | {r['status']}\n{r['detail']}" for r in rows]))
async def seats(update,context):
    if not is_admin(update.effective_user.id): return
    con=db(); n=con.execute("SELECT COUNT(*) n FROM students WHERE status='Approved'").fetchone()["n"]; con.close()
    await update.message.reply_text(f"कुल क्षमता: 120\nस्वीकृत: {n}\nशेष (अनुमानित): {max(0,120-n)}")
async def approve(update,context):
    if not is_admin(update.effective_user.id) or not context.args: return
    uid=int(context.args[0]); con=db(); con.execute("UPDATE students SET status='Approved' WHERE tg_id=?",(uid,)); con.commit(); con.close()
    await context.bot.send_message(uid,"🎉 आपका Matsya Library Alwar admission approve हो गया है। सीट आवंटन के लिए Admin से संपर्क करें।")
    await update.message.reply_text("Admission approved.")
async def fee(update,context):
    if not is_admin(update.effective_user.id) or len(context.args)<2: return
    uid=int(context.args[0]); status="Paid" if context.args[1].lower()=="paid" else "Pending"
    con=db(); con.execute("UPDATE students SET fee_status=? WHERE tg_id=?",(status,uid)); con.commit(); con.close()
    await context.bot.send_message(uid,f"आपकी Library fee status: {status}")
    await update.message.reply_text("Fee status updated.")
async def assign(update,context):
    if not is_admin(update.effective_user.id) or len(context.args)<2: return
    uid=int(context.args[0]); seat=context.args[1]
    con=db(); con.execute("UPDATE students SET seat=? WHERE tg_id=?",(seat,uid)); con.commit(); con.close()
    await context.bot.send_message(uid,f"आपकी Matsya Library seat आवंटित की गई है: {seat}")
    await update.message.reply_text("Seat assigned.")
async def broadcast(update,context):
    if not is_admin(update.effective_user.id) or not context.args: return
    msg=" ".join(context.args); con=db(); ids=[r["tg_id"] for r in con.execute("SELECT tg_id FROM students").fetchall()]; con.close()
    sent=0
    for uid in ids:
        try: await context.bot.send_message(uid,msg); sent+=1
        except Exception: pass
    await update.message.reply_text(f"Broadcast sent: {sent}")

def main():
    if not TOKEN: raise RuntimeError("BOT_TOKEN environment variable is missing.")
    db()
    app=Application.builder().token(TOKEN).build()
    conv=ConversationHandler(
      entry_points=[MessageHandler(filters.Regex("^📝 Online Admission$"),admission),
                    MessageHandler(filters.Regex("^🛠️ Submit Complaint$"),complaint_start)],
      states={
        NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND,get_name)],
        PHONE:[MessageHandler(filters.CONTACT | filters.TEXT & ~filters.COMMAND,get_phone)],
        PLAN:[CallbackQueryHandler(get_plan,pattern="^plan:")],
        COMPLAINT:[MessageHandler(filters.TEXT & ~filters.COMMAND,complaint_category)],
        SEAT:[MessageHandler(filters.TEXT & ~filters.COMMAND,complaint_detail)],
      }, fallbacks=[CommandHandler("cancel",cancel),MessageHandler(filters.Regex("^❌ रद्द करें$"),cancel)],
      allow_reentry=True)
    app.add_handler(CommandHandler("start",start))
    app.add_handler(conv)
    app.add_handler(CommandHandler("admin",admin))
    app.add_handler(CommandHandler("students",students))
    app.add_handler(CommandHandler("complaints",complaints))
    app.add_handler(CommandHandler("seats",seats))
    app.add_handler(CommandHandler("approve",approve))
    app.add_handler(CommandHandler("fee",fee))
    app.add_handler(CommandHandler("assign",assign))
    app.add_handler(CommandHandler("broadcast",broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_router))
    logging.basicConfig(level=logging.INFO)
    app.run_polling()

if __name__=="__main__": main()
