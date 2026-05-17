import os
import tempfile
import aiohttp
import base64
import google.generativeai as genai
from telegram import Update
from telegram.ext import ContextTypes
from database import get_user, update_user
from ai_brain import analyze_voice
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    await update.message.reply_text("🎧 שומע אותך... רגע!")

    voice = update.message.voice or update.message.audio
    file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    await file.download_to_drive(tmp_path)

    try:
        transcribed = await transcribe_audio(tmp_path)
        if not transcribed:
            await update.message.reply_text("❌ לא הצלחתי להבין את ההקלטה. נסה שוב.")
            return

        task = user.get('current_topic', 'דבר באנגלית בחופשיות')
        analysis = await analyze_voice(user, transcribed, task)

        feedback_text = (
            f"🎤 *מה שמעתי:*\n_{transcribed}_\n\n"
            f"📝 *ניתוח:*\n{analysis}"
        )
        await update.message.reply_text(feedback_text, parse_mode="Markdown")

        audio_response = await text_to_speech(analysis)
        if audio_response:
            await update.message.reply_voice(audio_response, caption="🔊 משוב קולי")

    except Exception as e:
        await update.message.reply_text(f"❌ שגיאה בעיבוד הקול: {str(e)}")
    finally:
        os.unlink(tmp_path)


async def transcribe_audio(audio_path: str) -> str:
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        response = model.generate_content([
            {
                "inline_data": {
                    "mime_type": "audio/ogg",
                    "data": audio_b64
                }
            },
            "Transcribe exactly what is said in this audio. Return only the transcription, nothing else."
        ])
        return response.text.strip()
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""


async def text_to_speech(text: str) -> bytes | None:
    try:
        tts_text = text[:500] if len(text) > 500 else text

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "text": tts_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.read()
                else:
                    print(f"ElevenLabs error: {await resp.text()}")
                    return None
    except Exception as e:
        print(f"TTS error: {e}")
        return None
