import os
import tempfile
import aiohttp
import aiofiles
from telegram import Update
from telegram.ext import ContextTypes
from database import get_user, update_user
from ai_brain import analyze_voice
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    await update.message.reply_text("🎧 שומע אותך... רגע!")

    # Download voice file
    voice = update.message.voice or update.message.audio
    file = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    await file.download_to_drive(tmp_path)

    try:
        # Transcribe with Whisper
        transcribed = await transcribe_with_whisper(tmp_path)
        if not transcribed:
            await update.message.reply_text("❌ לא הצלחתי להבין את ההקלטה. נסה שוב.")
            return

        # Analyze the speech
        task = user.get('current_topic', 'דבר באנגלית בחופשיות')
        analysis = await analyze_voice(user, transcribed, task)

        # Send text feedback
        feedback_text = (
            f"🎤 *מה שמעתי:*\n_{transcribed}_\n\n"
            f"📝 *ניתוח:*\n{analysis}"
        )
        await update.message.reply_text(feedback_text, parse_mode="Markdown")

        # Generate audio response with ElevenLabs
        audio_response = await text_to_speech(analysis)
        if audio_response:
            await update.message.reply_voice(audio_response, caption="🔊 משוב קולי")

    except Exception as e:
        await update.message.reply_text(f"❌ שגיאה בעיבוד הקול: {str(e)}")
    finally:
        os.unlink(tmp_path)

async def transcribe_with_whisper(audio_path: str) -> str:
    """Transcribe audio using local Whisper model"""
    try:
        import whisper
        model = whisper.load_model("base")  # base is fast and good enough
        result = model.transcribe(audio_path, language="en")
        return result["text"].strip()
    except ImportError:
        # Fallback: try using ffmpeg + basic approach
        return await transcribe_fallback(audio_path)

async def transcribe_fallback(audio_path: str) -> str:
    """Fallback transcription if whisper not installed"""
    return "שגיאה: Whisper לא מותקן. הרץ: pip install openai-whisper"

async def text_to_speech(text: str) -> bytes | None:
    """Convert text to speech using ElevenLabs"""
    try:
        # Limit text length for TTS
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
                    audio_bytes = await resp.read()
                    return audio_bytes
                else:
                    error = await resp.text()
                    print(f"ElevenLabs error: {error}")
                    return None
    except Exception as e:
        print(f"TTS error: {e}")
        return None

async def send_audio_lesson(bot, chat_id: int, text: str, caption: str = ""):
    """Send a lesson as audio - good for vocabulary and pronunciation"""
    audio = await text_to_speech(text)
    if audio:
        await bot.send_voice(chat_id=chat_id, voice=audio, caption=caption)
