from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user, create_user, update_user, update_streak
from config import ENGLISH_LEVELS, MATH_LEVELS

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔤 אנגלית", callback_data="subject_english"),
            InlineKeyboardButton("🔢 מתמטיקה", callback_data="subject_math"),
        ],
        [
            InlineKeyboardButton("📊 ההתקדמות שלי", callback_data="show_progress"),
            InlineKeyboardButton("🎯 מבחן מיקום", callback_data="diagnostic_menu"),
        ],
        [
            InlineKeyboardButton("🔥 אתגר יומי", callback_data="daily_challenge"),
        ]
    ])

def english_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 דקדוק", callback_data="eng_grammar"),
            InlineKeyboardButton("✍️ כתיבה", callback_data="eng_writing"),
        ],
        [
            InlineKeyboardButton("👁️ קריאה", callback_data="eng_reading"),
            InlineKeyboardButton("🎤 דיבור", callback_data="eng_speaking"),
        ],
        [
            InlineKeyboardButton("📝 מילון יומי", callback_data="eng_vocab"),
            InlineKeyboardButton("🧪 מבחן", callback_data="eng_quiz"),
        ],
        [InlineKeyboardButton("⬅️ חזרה", callback_data="main_menu")]
    ])

def math_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ חשבון", callback_data="math_arithmetic"),
            InlineKeyboardButton("📐 גאומטריה", callback_data="math_geometry"),
        ],
        [
            InlineKeyboardButton("🔡 אלגברה", callback_data="math_algebra"),
            InlineKeyboardButton("📊 סטטיסטיקה", callback_data="math_stats"),
        ],
        [
            InlineKeyboardButton("∫ חדו\"א", callback_data="math_calculus"),
            InlineKeyboardButton("🧪 מבחן", callback_data="math_quiz"),
        ],
        [InlineKeyboardButton("⬅️ חזרה", callback_data="main_menu")]
    ])

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name

    user = get_user(user_id)
    if not user:
        user = create_user(user_id, username)
        welcome = (
            f"🎓 *ברוך הבא ל-MegaLearnBot, {username}!*\n\n"
            "אני הבוט החכם ביותר ללימוד *אנגלית ומתמטיקה* 🚀\n\n"
            "אני אתאים את עצמי בדיוק לרמה שלך, אזכור כל טעות שתעשה, "
            "ואדאג שתתקדם מהר ובאופן מהנה.\n\n"
            "📌 *מה אני יכול לעשות?*\n"
            "• ללמד שיעורים מותאמים אישית\n"
            "• לבדוק תשובות ולהסביר טעויות\n"
            "• לשמוע אותך מדבר ולתת משוב על הגייה 🎤\n"
            "• לעקוב אחרי ההתקדמות שלך\n"
            "• לתת אתגר יומי עם XP ורמות\n\n"
            "👇 *בחר מה תרצה ללמוד:*"
        )
    else:
        update_streak(user_id)
        eng = ENGLISH_LEVELS.get(user['english_level'], 'מתחיל')
        math = MATH_LEVELS.get(user['math_level'], 'מתחיל')
        welcome = (
            f"👋 *ברוך השב, {username}!*\n\n"
            f"🔤 אנגלית: {eng}\n"
            f"🔢 מתמטיקה: {math}\n"
            f"🔥 Streak: {user['streak']} ימים\n\n"
            "מה נלמד היום?"
        )

    await update.effective_message.reply_text(
        welcome, parse_mode="Markdown", reply_markup=main_menu_keyboard()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    user = get_user(user_id)

    if data == "main_menu":
        await query.edit_message_text(
            "🏠 *תפריט ראשי* — מה נלמד?",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    elif data == "subject_english":
        await query.edit_message_text(
            f"🔤 *אנגלית* — רמה {user['english_level']}/9\nבחר נושא:",
            parse_mode="Markdown",
            reply_markup=english_menu_keyboard()
        )

    elif data == "subject_math":
        await query.edit_message_text(
            f"🔢 *מתמטיקה* — רמה {user['math_level']}/9\nבחר נושא:",
            parse_mode="Markdown",
            reply_markup=math_menu_keyboard()
        )

    elif data == "show_progress":
        text = (
            f"📊 *ההתקדמות שלך*\n\n"
            f"🔤 אנגלית — רמה {user['english_level']}/9 | XP: {user['english_xp']}/200\n"
            f"🔢 מתמטיקה — רמה {user['math_level']}/9 | XP: {user['math_xp']}/200\n\n"
            f"🔥 Streak: {user['streak']} ימים\n"
            f"✅ שיעורים: {user['lessons_done']}\n"
            f"⭐ ממוצע: {user['avg_score']}%"
        )
        wp = user.get('weak_points', {})
        if wp:
            top_weak = sorted(wp.items(), key=lambda x: -x[1])[:3]
            text += "\n\n⚠️ *נקודות לחיזוק:*\n" + "\n".join(f"• {k.split(':')[1]}" for k, v in top_weak)
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 חזרה", callback_data="main_menu")
            ]]))

    elif data.startswith("eng_") or data.startswith("math_"):
        await handle_topic_callback(query, user, data)

    elif data == "diagnostic_menu":
        await query.edit_message_text(
            "🎯 *מבחן מיקום*\n\nבחר מקצוע לאבחון:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔤 אנגלית", callback_data="diag_english"),
                 InlineKeyboardButton("🔢 מתמטיקה", callback_data="diag_math")],
                [InlineKeyboardButton("⬅️ חזרה", callback_data="main_menu")]
            ])
        )

    elif data in ("diag_english", "diag_math"):
        subject = "english" if data == "diag_english" else "math"
        update_user(user_id, current_subject=subject, current_topic="diagnostic",
                    awaiting_answer=1, current_question="diagnostic_start")
        from ai_brain import run_diagnostic
        response = await run_diagnostic(user, subject, [])
        await query.edit_message_text(
            f"🎯 *מבחן מיקום — {'אנגלית' if subject == 'english' else 'מתמטיקה'}*\n\n{response}",
            parse_mode="Markdown"
        )

    elif data == "daily_challenge":
        import random
        subjects = ["english", "math"]
        subject = random.choice(subjects)
        topics_eng = ["Present Perfect", "Conditionals", "Passive Voice", "Idioms"]
        topics_math = ["Quadratic Equations", "Pythagorean theorem", "Fractions", "Percentages"]
        topic = random.choice(topics_eng if subject == "english" else topics_math)
        
        update_user(user_id, current_subject=subject, current_topic=topic, awaiting_answer=1)
        from ai_brain import generate_quiz
        response = await generate_quiz(user, subject, topic)
        await query.edit_message_text(
            f"🔥 *אתגר יומי!*\n\n{response}\n\n_ענה בהודעה חופשית_",
            parse_mode="Markdown"
        )

async def handle_topic_callback(query, user, data: str):
    user_id = query.from_user.id
    topics_map = {
        "eng_grammar": ("english", "grammar", "דקדוק"),
        "eng_writing": ("english", "writing", "כתיבה"),
        "eng_reading": ("english", "reading", "קריאה"),
        "eng_speaking": ("english", "speaking", "דיבור"),
        "eng_vocab": ("english", "vocabulary", "אוצר מילים"),
        "eng_quiz": ("english", "quiz", "מבחן"),
        "math_arithmetic": ("math", "arithmetic", "חשבון"),
        "math_geometry": ("math", "geometry", "גאומטריה"),
        "math_algebra": ("math", "algebra", "אלגברה"),
        "math_stats": ("math", "statistics", "סטטיסטיקה"),
        "math_calculus": ("math", "calculus", "חדו\"א"),
        "math_quiz": ("math", "quiz", "מבחן"),
    }
    
    subject, topic, topic_heb = topics_map.get(data, ("english", "grammar", "דקדוק"))
    update_user(user_id, current_subject=subject, current_topic=topic, awaiting_answer=0)
    
    if topic == "quiz":
        from ai_brain import generate_quiz
        response = await generate_quiz(user, subject, topic_heb)
        update_user(user_id, awaiting_answer=1, current_question=response[:200])
        await query.edit_message_text(
            f"🧪 *מבחן {'אנגלית' if subject == 'english' else 'מתמטיקה'}*\n\n{response}",
            parse_mode="Markdown"
        )
    elif topic == "speaking":
        await query.edit_message_text(
            "🎤 *תרגול דיבור*\n\n"
            "שלח לי *הודעה קולית* ואני אנתח את ההגייה והניסוח שלך!\n\n"
            "נסה להגיד: _'Tell me about your day in 3 sentences'_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ חזרה", callback_data="subject_english")
            ]])
        )
    else:
        from ai_brain import generate_lesson
        response = await generate_lesson(user, subject, topic_heb)
        update_user(user_id, awaiting_answer=1, current_question=response[:200])
        back_btn = "subject_english" if subject == "english" else "subject_math"
        await query.edit_message_text(
            f"📚 *{topic_heb}*\n\n{response}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ חזרה", callback_data=back_btn)
            ]])
        )
