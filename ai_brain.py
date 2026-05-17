import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, ENGLISH_LEVELS, MATH_LEVELS

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

def build_system_prompt(user: dict, mode: str = "teach") -> str:
    eng_level_name = ENGLISH_LEVELS.get(user['english_level'], "מתחיל")
    math_level_name = MATH_LEVELS.get(user['math_level'], "מתחיל")
    weak = user.get('weak_points', {})
    weak_str = ", ".join(f"{k.split(':')[1]} ({v} טעויות)" for k, v in weak.items()) if weak else "אין עדיין"

    base = f"""אתה MegaLearnBot — מורה AI מתקדם ומעורר השראה שמלמד אנגלית ומתמטיקה.

פרטי הלומד:
- רמת אנגלית: {eng_level_name} (רמה {user['english_level']}/9)
- רמת מתמטיקה: {math_level_name} (רמה {user['math_level']}/9)  
- שיעורים שהושלמו: {user['lessons_done']}
- נקודות חולשה: {weak_str}
- ממוצע ציונים: {user['avg_score']}%

עקרונות הוראה:
1. תמיד מסביר בעברית, אבל מלמד באנגלית/מתמטיקה
2. מותאם בדיוק לרמה — לא קל מדי, לא קשה מדי
3. מעודד ומחזק ביטחון עצמי
4. אם הלומד טועה — מסביר למה, לא רק את הנכון
5. משתמש בדוגמאות מהחיים האמיתיים
6. קצר וממוקד — לא יותר מ-200 מילים בכל הסבר
"""

    if mode == "teach":
        base += "\nמצב: הוראה. תלמד את הנושא המבוקש ובסוף שאל שאלה אחת לבדיקת הבנה."
    elif mode == "quiz":
        base += "\nמצב: מבחן. שאל שאלה אחת ברורה, תן 4 אפשרויות (א/ב/ג/ד), המתן לתשובה."
    elif mode == "check":
        base += "\nמצב: בדיקת תשובה. בדוק אם הלומד צדק, הסבר למה, ותן ניקוד 0-100."
    elif mode == "diagnostic":
        base += "\nמצב: אבחון. שאל שאלה לאיתור הרמה המדויקת של הלומד."
    elif mode == "voice_feedback":
        base += "\nמצב: משוב על דיבור. נתחת את ההגייה והניסוח, תן משוב ספציפי."

    return base

async def ask_gemini(user: dict, user_message: str, mode: str = "teach") -> str:
    system = build_system_prompt(user, mode)
    history = user.get('conversation_history', [])[-10:]  # last 10 messages

    contents = []
    for msg in history:
        contents.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    full_prompt = system + "\n\n" + "\n".join(
        f"{'משתמש' if m['role']=='user' else 'מורה'}: {m['parts'][0]['text']}"
        for m in contents
    )

    response = model.generate_content(full_prompt)
    return response.text

async def generate_lesson(user: dict, subject: str, topic: str) -> str:
    prompt = f"למד אותי עכשיו את הנושא: {topic} ב{'אנגלית' if subject == 'english' else 'מתמטיקה'}"
    return await ask_gemini(user, prompt, mode="teach")

async def generate_quiz(user: dict, subject: str, topic: str) -> str:
    prompt = f"שאל אותי שאלת מבחן על: {topic} ב{'אנגלית' if subject == 'english' else 'מתמטיקה'}"
    return await ask_gemini(user, prompt, mode="quiz")

async def check_answer(user: dict, question: str, answer: str) -> tuple[str, int]:
    prompt = f"השאלה הייתה: {question}\nהתשובה שלי: {answer}\nבדוק אם צדקתי ותן ניקוד."
    response = await ask_gemini(user, prompt, mode="check")
    
    score = 100
    lower = response.lower()
    if "טועה" in lower or "לא נכון" in lower or "שגוי" in lower:
        score = 0
    elif "חלקי" in lower or "כמעט" in lower:
        score = 50
    
    return response, score

async def run_diagnostic(user: dict, subject: str, answers_so_far: list) -> str:
    context = "\n".join(f"ש: {a['q']} | ת: {a['a']} | תוצאה: {a['result']}" for a in answers_so_far)
    prompt = f"אבחון {'אנגלית' if subject == 'english' else 'מתמטיקה'}.\n{context}\nשאל את השאלה הבאה לאיתור הרמה."
    return await ask_gemini(user, prompt, mode="diagnostic")

async def analyze_voice(user: dict, transcribed_text: str, task: str) -> str:
    prompt = f"הלומד התבקש: {task}\nמה שנאמר (תמלול): {transcribed_text}\nנתח את הדיבור ותן משוב."
    return await ask_gemini(user, prompt, mode="voice_feedback")
