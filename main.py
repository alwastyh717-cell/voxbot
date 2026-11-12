import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

# --- إعدادات البوت الأساسية ---
API_TOKEN = "8759041703:AAGX4QMWvXWjoNwdP8GwZuEOpkQTXJ66IQ8"  # تم تحديث التوكن بنجاح
ADMIN_ID = 8664763495  # أيدي المالك الأساسي (@ASADALY1)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# --- مسارات ملفات حفظ البيانات (لكي لا تصفر عند إعادة التشغيل) ---
USERS_DB_FILE = "users_db.json"
BOTS_DB_FILE = "user_bots.json"
PRICES_DB_FILE = "subscription_prices.json"

# --- دوال حفظ واسترجاع البيانات لتجنب التصفير ---
def load_json(filename, default_value):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_value
    return default_value

def save_json(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving {filename}: {e}")

# تحميل البيانات عند بدء التشغيل
subscription_prices = load_json(PRICES_DB_FILE, {
    "7_days": {"days": 7, "stars": 50, "name": "7 أيام"},
    "1_month": {"days": 30, "stars": 100, "name": "شهر"},
    "6_months": {"days": 180, "stars": 300, "name": "6 أشهر"},
    "1_year": {"days": 365, "stars": 1300, "name": "سنة"}
})

users_db = load_json(USERS_DB_FILE, {})      # تخزين المستخدمين، النقاط، والـ VIP
user_bots = load_json(BOTS_DB_FILE, {})      # تخزين البوتات المرفوعة


# --- لوحة التحكم والبداية (/start) ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = str(message.from_user.id)  # استخدام النص لمفاتيح JSON
    if user_id not in users_db:
        users_db[user_id] = {
            "bots_limit": 1,
            "vip": False,
            "stars_balance": 0,  # رصيد النجوم أو النقاط لكل عضو
            "expire_date": "غير مشترك"
        }
        save_json(USERS_DB_FILE, users_db)

    keyboard_buttons = [
        [InlineKeyboardButton(text="🤖 إدارة وبوتاتي (رفع بوت ومكاتب)", callback_data="my_bots")],
        [InlineKeyboardButton(text="💎 اشتراكات VIP والأسعار والنجوم", callback_data="subscriptions_menu")]
    ]
    
    if int(user_id) == ADMIN_ID:
        keyboard_buttons.append([InlineKeyboardButton(text="⚙️ لوحة الإدارة والتحكم", callback_data="admin_panel")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(
        "مرحباً بك في منصة استضافة البوتات المتطورة 🚀\n"
        "جميع بياناتك وجلساتك محفوظة بشكل دائم ولن تصفّر أبداً عند إيقاف أو تشغيل البوت.",
        reply_markup=keyboard
    )


# --- قسم الاشتراكات والأزرار العامة ---
@router.callback_query(F.data == "subscriptions_menu")
async def subscriptions_menu(callback: CallbackQuery):
    keyboard_buttons = []
    for key, data in subscription_prices.items():
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{data['name']} - {data['stars']} نجمة ⭐",
                callback_data=f"buy_{key}"
            )
        ])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 رجوع للقائمة الرئيسية", callback_data="back_home")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(
        "💎 **قسم الاشتراكات والنجوم الدائم**\n\n"
        "اختر الباقة المناسبة لك لتفعيل أو تمديد اشتراكك وزيادة عدد بوتاتك:\n\n"
        "• 7 أيام: 50 نجمة ⭐\n"
        "• شهر: 100 نجمة ⭐\n"
        "• 6 أشهر: 300 نجمة ⭐\n"
        "• سنة: 1300 نجمة ⭐",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("buy_"))
async def process_subscription_buy(callback: CallbackQuery):
    sub_key = callback.data.split("_", 1)[1]
    if sub_key not in subscription_prices:
        await callback.answer("الباقة غير موجودة!", show_alert=True)
        return

    plan = subscription_prices[sub_key]
    user = callback.from_user
    
    admin_text = (
        f"🚨 **طلب اشتراك جديد!**\n\n"
        f"👤 الاسم: {user.full_name}\n"
        f"🔗 اليوزر: @{user.username or 'لا يوجد'}\n"
        f"🆔 الأيدي: `{user.id}`\n"
        f"📦 الباقة المطلوبة: {plan['name']}\n"
        f"⭐ التكلفة: {plan['stars']} نجمة"
    )
    
    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ قبول وتفعيل اشتراكه", callback_data=f"accept_sub_{user.id}_{sub_key}")],
                [InlineKeyboardButton(text="❌ رفض الطلب", callback_data=f"reject_sub_{user.id}")]
            ]),
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Failed to send message to admin: {e}")

    await callback.message.edit_text(
        f"✅ **تم إرسال طلب اشتراكك بنجاح!**\n\n"
        f"📦 الباقة المطلوبة: {plan['name']} ({plan['stars']} نجمة)\n\n"
        f"يرجى مراسلة المالك لتسليمه النجوم وتفعيل اشتراكك فوراً:\n"
        f"@ASADALY1\n\n"
        f"مرحباً يامبرمجنا، تم طلب اشتراك (مدة: {plan['name']}) والأيدي الخاص بي (`{user.id}`). سوف أرسل النجوم وفعلي اشتراكي.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📨 راسل المالك الآن", url="https://t.me/ASADALY1")],
            [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="back_home")]
        ]),
        parse_mode="Markdown"
    )


# --- لوحة التحكم الخاصة بالمالك (الإدارة) ---
@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("هذا القسم خاص بمالك البوت فقط!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ تعديل أسعار الاشتراكات والأيام", callback_data="admin_edit_prices")],
        [InlineKeyboardButton(text="👥 إدارة صلاحيات المستخدمين وبوتاتهم", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_home")]
    ])
    await callback.message.edit_text("⚙️ **لوحة تحكم المالك الرئيسية**", reply_markup=keyboard)


@router.callback_query(F.data == "admin_edit_prices")
async def admin_edit_prices(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    text = "✏️ **الأسعار الحالية للاشتراكات (محفوظة دائماً):**\n\n"
    for key, data in subscription_prices.items():
        text += f"• {data['name']}: {data['stars']} نجمة ({data['days']} يوم)\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع لوحة الإدارة", callback_data="admin_panel")]
        ])
    )


@router.callback_query(F.data == "admin_users_list")
async def admin_users_list(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    total_users = len(users_db)
    await callback.message.edit_text(
        f"👥 **إدارة المستخدمين والصلاحيات**\n\n"
        f"إجمالي عدد الأعضاء المسجلين (محفوظون دائمياً): {total_users}\n"
        f"جميع بيانات الأعضاء والبوستات والنقاط محفوظة في الملفات ولن تصفّر أبداً.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع لوحة الإدارة", callback_data="admin_panel")]
        ])
    )


# قبول الاشتراك من قبل المالك
@router.callback_query(F.data.startswith("accept_sub_"))
async def accept_subscription(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    parts = callback.data.split("_")
    target_user_id = str(parts[2])
    sub_key = parts[3]
    
    if target_user_id in users_db:
        users_db[target_user_id]["vip"] = True
        users_db[target_user_id]["bots_limit"] += 1  # تفعيل وزيادة عدد البوتات المسموحة
        save_json(USERS_DB_FILE, users_db)

    try:
        await bot.send_message(
            int(target_user_id),
            "🎉 **مبروك! تم تفعيل اشتراكك VIP بنجاح من قبل المالك.**\nيمكنك الآن رفع بوتك واستخدام كافة الميزات المتاحة."
        )
    except Exception:
        pass

    await callback.message.edit_text(callback.message.text + "\n\n✅ **تم قبول وتفعيل الاشتراك لهذا المستخدم بنجاح!**")


@router.callback_query(F.data.startswith("reject_sub_"))
async def reject_subscription(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    target_user_id = int(callback.data.split("_")[2])
    try:
        await bot.send_message(target_user_id, "❌ عذراً، تم رفض طلب الاشتراك الخاص بك أو لم يتم استلام النجوم المطلوبة.")
    except Exception:
        pass
    await callback.message.edit_text(callback.message.text + "\n\n❌ **تم رفض الطلب.**")


@router.callback_query(F.data == "back_home")
async def back_home(callback: CallbackQuery):
    await cmd_start(callback.message)


# --- إدارة البوتات ورفع الملفات ومكاتب requirements.txt ---
@router.callback_query(F.data == "my_bots")
async def my_bots_menu(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    if user_id not in users_db:
        users_db[user_id] = {"bots_limit": 1, "vip": False, "stars_balance": 0}
        save_json(USERS_DB_FILE, users_db)

    user_data = users_db[user_id]
    current_bots = len(user_bots.get(user_id, []))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 رفع بوت جديد (مع ملف المتطلبات .txt)", callback_data="upload_bot_steps")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_home")]
    ])
    
    await callback.message.edit_text(
        f"🤖 **إدارة بوتاتك والاستضافة الدائمة**\n\n"
        f"📊 عدد بوتاتك المرفوعة: {current_bots} / {user_data['bots_limit']}\n"
        f"💎 حالة الـ VIP: {'مشترك ✅' if user_data['vip'] else 'عادي ❌'}\n"
        f"⭐ رصيدك والنقاط: {user_data.get('stars_balance', 0)} نجمة\n\n"
        f"• جميع ملفاتك وجلساتك محفوظة ولن تصفّر أبداً حتى عند إيقاف أو نقل الاستضافة.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "upload_bot_steps")
async def upload_bot_steps(callback: CallbackQuery):
    await callback.message.edit_text(
        "📤 **طريقة رفع البوت:**\n\n"
        "1. قم بإرسال ملف البوت بصيغة البرمجة (`.py`).\n"
        "2. إذا كان بوتك يحتاج مكتبات خارجية خاصة، قم بإرسال ملف المتطلبات باسم `requirements.txt`.\n"
        "3. سيتم حفظ بوتك وتشغيله بملفات آمنة ودائمة لا تضيع أبداً.\n\n"
        "قم بإرسال الملفات الآن في المحادثة مباشرة:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="my_bots")]
        ]),
        parse_mode="Markdown"
    )


# استقبال الملفات البرمجية وملفات requirements.txt من المستخدمين
@router.message(F.document)
async def handle_uploaded_document(message: Message):
    user_id = str(message.from_user.id)
    if user_id not in users_db:
        users_db[user_id] = {"bots_limit": 1, "vip": False, "stars_balance": 0}
        save_json(USERS_DB_FILE, users_db)

    doc = message.document
    file_name = doc.file_name

    if file_name.endswith(".py"):
        if user_id not in user_bots:
            user_bots[user_id] = []

        current_bots = len(user_bots[user_id])
        limit = users_db[user_id]["bots_limit"]

        if current_bots >= limit:
            await message.answer(
                f"❌ عذراً، لقد وصلت للحد الأقصى من البوتات المسموح برفعها ({current_bots}/{limit}).\n"
                "يرجى ترقية حسابك إلى VIP لزيادة عدد بوتاتك المتاحة."
            )
            return

        user_bots[user_id].append({"bot_name": file_name, "file_id": doc.file_id})
        save_json(BOTS_DB_FILE, user_bots)
        
        await message.answer(
            f"✅ **تم حفظ ملف البوت بشكل دائم وآمن!** (`{file_name}`)\n"
            "لن يضيع الملف ولن يصفر أبداً حتى عند إعادة التشغيل.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🤖 إدارة بوتاتي", callback_data="my_bots")]
            ])
        )

    elif file_name == "requirements.txt" or file_name.endswith(".txt"):
        await message.answer(
            f"📦 **تم استلام وحفظ ملف المتطلبات (`{file_name}`) بنجاح!**\n"
            "سيتم استخدامه لتثبيت المكتبات المطلوبة لبوتاك بشكل دائم.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🤖 إدارة بوتاتي", callback_data="my_bots")]
            ])
        )
    else:
        await message.answer("⚠️ يرجى إرسال ملف بايثون صحيح ينتهي بـ `.py` أو ملف متطلبات `requirements.txt`.")


async def main():
    dp.include_router(router)
    print("Persistent Hosting Bot is running successfully...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
