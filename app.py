import os
import cv2
import pyttsx3
import speech_recognition as sr
from flask import Flask, request, render_template_string
from PyPDF2 import PdfReader
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key="YOUR_API_KEY")

engine = pyttsx3.init()
recognizer = sr.Recognizer()

questions = []
answers = []
domain = ""

# ======================
# HTML UI
# ======================
HTML = """
<h1>AI Interviewer</h1>

<form action="/upload" method="post" enctype="multipart/form-data">
  <input type="file" name="file">
  <button type="submit">Upload Resume</button>
</form>

<br>

<form action="/start">
  <button type="submit">Start Interview</button>
</form>

<br>

<form action="/evaluate">
  <button type="submit">Get Result</button>
</form>
"""

# ======================
# VOICE
# ======================
def speak(text):
    print("AI:", text)
    engine.say(text)
    engine.runAndWait()

def listen():
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print("User:", text)
        return text
    except:
        return "Could not understand"

# ======================
# CAMERA
# ======================
def start_camera():
    cap = cv2.VideoCapture(0)

    print("Camera ON (press Q to exit preview)")

    while True:
        ret, frame = cap.read()
        cv2.imshow("Interview Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# ======================
# HOME
# ======================
@app.route("/")
def home():
    return render_template_string(HTML)

# ======================
# UPLOAD
# ======================
@app.route("/upload", methods=["POST"])
def upload():
    global domain

    file = request.files["file"]
    path = os.path.join("uploads", file.filename)
    file.save(path)

    reader = PdfReader(path)
    text = ""

    for page in reader.pages:
        text += page.extract_text()

    prompt = f"""
    Analyze resume and tell:
    - Domain
    - Skills

    {text}
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    domain = res.choices[0].message.content

    return f"<h2>Detected:</h2><p>{domain}</p><a href='/'>Back</a>"

# ======================
# START INTERVIEW
# ======================
@app.route("/start")
def start():
    global questions, answers
    answers = []

    prompt = f"Generate 5 interview questions for {domain}"

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    questions = [q.strip() for q in res.choices[0].message.content.split("\n") if len(q) > 5]

    # Start camera
    start_camera()

    # Interview loop
    for q in questions:
        speak(q)
        ans = listen()

        answers.append({
            "question": q,
            "answer": ans
        })

    return "<h2>Interview Finished</h2><a href='/'>Go Back</a>"

# ======================
# EVALUATE
# ======================
@app.route("/evaluate")
def evaluate():
    qa_text = ""

    for qa in answers:
        qa_text += f"Q: {qa['question']}\nA: {qa['answer']}\n\n"

    prompt = f"""
    Evaluate this interview:

    {qa_text}

    Give:
    - Score out of 10
    - Strengths
    - Weaknesses
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    result = res.choices[0].message.content

    return f"<h2>Result</h2><pre>{result}</pre><a href='/'>Back</a>"

# ======================
# RUN
# ======================
if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True)