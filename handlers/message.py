from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_user, update_user, add_xp, record_score, add_weak_point
from ai_brain import check_answer, ask_gemini
from config import XP_PER_CORRECT, XP_PER_LESSON

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    text = update.message.text.strip()

    if not user:
        await update.message.reply_text("שלח /start להתחלה!")
        return

    # Save to conversation history
    history = user.get('conversation_history', [])
    history.append({"role": "user", "content": text})
    if len(history) > 20:
        history = history[-20:]

    subject = user.get('current_subject', 'none')
    topic = user.get('current_topic', '')
    awaiting = user.get('awaiting_answer', 0)

    if subject == 'none':
        # Free chat mode
        response = await ask_gemini(user, text, mode="teach")
        history.append({"role": "model", "content": response})
        update_user(user_id, conversation_history=history)
        await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 תפריט", callback_data="main_menu")
        ]]))
        return

    if awaiting and topic == "diagnostic_start":
        await handle_diagnostic_answer(update, user, text, subject, history)
        return

    if awaiting and user.get('current_question'):
        await handle_quiz_answer(update, user, text, subject, topic, history)
        return

    # General question in subject context
    response = await ask_gemini(user, text, mode="teach")
    history.append({"role": "model", "content": response})
    update_user(user_id, conversation_history=history)
    await update.message.reply_text(response, reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 תפריט", callback_data="main_menu")
    ]]))

async def handle_quiz_answer(update, user, answer, subject, topic, history):
    user_id = update.effective_user.id
    question = user.get('current_question', '')
    
    feedback, score = await check_answer(user, question, answer)
    history.append({"role": "model", "content": feedback})

    leveled_up = False
    if score >= 70:
        leveled_up, new_level = add_xp(user_id, subject, XP_PER_CORRECT)
        record_score(user_id, score)
        emoji = "✅"
    else:
        record_score(user_id, score)
        add_weak_point(user_id, subject, topic)
        emoji = "❌"

    score_bar = "█" * (score // 10) + "░" * (10 - score // 10)
    result_text = f"{emoji} *ניקוד: {score}/100*\n[{score_bar}]\n\n{feedback}"

    if leveled_up:
        from config import ENGLISH_LEVELS, MATH_LEVELS
        level_map = ENGLISH_LEVELS if subject == "english" else MATH_LEVELS
        result_text += f"\n\n🎉 *עלית רמה! ➜ רמה {new_level}: {level_map[new_level]}*"

    update_user(user_id,
        conversation_history=history,
        awaiting_answer=0,
        current_question=""
    )

    keyboard = [
        [
            InlineKeyboardButton("🔄 שאלה נוספת", callback_data=f"{'eng' if subject == 'english' else 'math'}_quiz"),
            InlineKeyboardButton("📚 שיעור", callback_data=f"{'eng' if subject == 'english' else 'math'}_grammar"),
        ],
        [InlineKeyboardButton("🏠 תפריט", callback_data="main_menu")]
    ]

    await update.message.reply_text(
        result_text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_diagnostic_answer(update, user, answer, subject, history):
    user_id = update.effective_user.id
    from ai_brain import run_diagnostic

    diag_history = user.get('weak_points', {}).get('_diag_answers', [])
    
    # Simple level detection based on answer quality
    feedback, score = await check_answer(user, user.get('current_question', ''), answer)
    
    result_entry = {"q": user.get('current_question', ''), "a": answer, "result": "נכון" if score >= 60 else "טועה"}
    diag_history.append(result_entry)

    if len(diag_history) >= 5:
        # Compute suggested level
        correct = sum(1 for r in diag_history if r['result'] == "נכון")
        suggested_level = min(correct + 1, 9)
        level_key = f"{subject}_level"

        update_user(user_id,
            **{level_key: suggested_level},
            current_topic="",
            awaiting_answer=0,
            current_question="diagnostic_done"
        )
        from config import ENGLISH_LEVELS, MATH_LEVELS
        level_map = ENGLISH_LEVELS if subject == "english" else MATH_LEVELS
        await update.message.reply_text(
            f"✅ *אבחון הושלם!*\n\n"
            f"ענית נכון על {correct}/5 שאלות.\n"
            f"הרמה שלך נקבעה ל: *{level_map[suggested_level]}*\n\n"
            f"עכשיו אני אתאים את השיעורים בדיוק לרמה שלך!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 תפריט ראשי", callback_data="main_menu")
            ]])
        )
    else:
        next_q = await run_diagnostic(user, subject, diag_history)
        update_user(user_id,
            conversation_history=history,
            current_question=next_q[:200],
            awaiting_answer=1
        )
        await update.message.reply_text(
            f"{feedback}\n\n---\n\n*שאלה {len(diag_history)+1}/5:*\n{next_q}",
            parse_mode="Markdown"
        )
