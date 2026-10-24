import os
import glob
import json
import requests
import streamlit as st
import pypdf

st.set_page_config(
    page_title="TI Asystent - Weryfikacja Quizów",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Asystent Weryfikacji Zadań - TI")
st.caption("Backend: OpenRouter (:free) | 100% Darmowy | Baza: CSV, Arkusze, PDF")

# Klucz API OpenRouter
api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Podaj OPENROUTER_API_KEY:", type="password")

if not api_key:
    st.warning("⚠️ Wymagany OPENROUTER_API_KEY. Dodaj w Secrets Streamlit lub w panelu bocznym.")
    st.info("Klucz pobierzesz za darmo z: https://openrouter.ai/keys")
    st.stop()

# Ścieżki
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPA_PATH = os.path.join(BASE_DIR, "mapa-quizow.md")
INSTRUKCJA_PATH = os.path.join(BASE_DIR, "INSTRUKCJA.md")
CSV_DIR = os.path.join(BASE_DIR, "dane-csv")
MAT_DIR = os.path.join(BASE_DIR, "materialy")

@st.cache_data
def get_base_instructions():
    mapa, instrukcja = "", ""
    if os.path.exists(MAPA_PATH):
        with open(MAPA_PATH, "r", encoding="utf-8") as f:
            mapa = f.read()
    if os.path.exists(INSTRUKCJA_PATH):
        with open(INSTRUKCJA_PATH, "r", encoding="utf-8") as f:
            instrukcja = f.read()
    return instrukcja, mapa

instrukcja_txt, mapa_txt = get_base_instructions()

SYSTEM_PROMPT = f"""
{instrukcja_txt}

MAPA QUIZÓW:
{mapa_txt}

ZASADY:
1. Odpowiadaj krótko i po polsku:
   Odpowiedź: [dokładny wynik/wartość]
   Ocena: poprawna / błędna / niejednoznaczna (jeśli podano propozycję użytkownika)
   Podstawa: [arkusz, komórki, strona PDF, formuła lub zarys obliczenia]
2. Dokładnie analizuj załączone dane tabelaryczne CSV i PDF.
3. Etykiety procentowe w wykresach kołowych Excela są liczbami całkowitymi bez miejsc po przecinku (np. 32%).
"""

# Wybór modelu i quizu w sidebarze
st.sidebar.header("Konfiguracja")
FREE_MODELS = [
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "cohere/north-mini-code:free",
    "thinkingmachines/inkling:free",
    "dots-studio/dots-3-note-preview:free"
]
selected_model = st.sidebar.selectbox("Model OpenRouter (wyłącznie :free):", FREE_MODELS)

quiz_choice = st.sidebar.selectbox(
    "Wybierz quiz:",
    ["Automatyczny (z pytania)", "Quiz 1", "Quiz 2", "Quiz 3", "Quiz 4", "Quiz 5", "Quiz 6", "Quiz 7"]
)

@st.cache_data
def load_all_materials():
    texts = {}
    if os.path.exists(MAT_DIR):
        for pdf_file in sorted(glob.glob(os.path.join(MAT_DIR, "*.pdf"))):
            fname = os.path.basename(pdf_file)
            try:
                reader = pypdf.PdfReader(pdf_file)
                full_text = []
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t:
                        full_text.append(f"--- Strona {idx+1} ---\n{t}")
                texts[fname] = "\n".join(full_text)
            except Exception as e:
                texts[fname] = f"Błąd odczytu PDF: {e}"
    return texts

pdf_materials = load_all_materials()

def get_context_for_quiz(q_num):
    chunks = []
    if q_num == 2:
        for f in glob.glob(os.path.join(CSV_DIR, "Podrozni_23__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                chunks.append(f"CSV {sheet}:\n{csv_f.read()}")
    elif q_num == 3:
        for f in glob.glob(os.path.join(CSV_DIR, "Ubezpiecznia-quiz_23__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                chunks.append(f"CSV {sheet}:\n{csv_f.read()}")
    elif q_num == 4:
        for f in glob.glob(os.path.join(CSV_DIR, "04_Delegacje_quiz__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                chunks.append(f"CSV {sheet}:\n{csv_f.read()}")
    elif q_num == 5:
        for f in glob.glob(os.path.join(CSV_DIR, "Dodatki_swiateczne_23__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                chunks.append(f"CSV {sheet}:\n{csv_f.read()}")
    elif q_num in [1, 6, 7]:
        for fname, txt in pdf_materials.items():
            chunks.append(f"PDF {fname}:\n{txt[:40000]}")
    return "\n\n".join(chunks)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_prompt = st.chat_input("Wpisz pytanie (np. 'Quiz 4: oblicz średnią liczbę dni delegacji dla Warszawy')")
if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    detected_quiz = None
    if "Quiz 1" in quiz_choice: detected_quiz = 1
    elif "Quiz 2" in quiz_choice: detected_quiz = 2
    elif "Quiz 3" in quiz_choice: detected_quiz = 3
    elif "Quiz 4" in quiz_choice: detected_quiz = 4
    elif "Quiz 5" in quiz_choice: detected_quiz = 5
    elif "Quiz 6" in quiz_choice: detected_quiz = 6
    elif "Quiz 7" in quiz_choice: detected_quiz = 7
    else:
        for q in [1, 2, 3, 4, 5, 6, 7]:
            if f"quiz {q}" in user_prompt.lower() or f"quiz{q}" in user_prompt.lower() or f"q{q}" in user_prompt.lower():
                detected_quiz = q
                break

    extra_context = ""
    if detected_quiz:
        with st.spinner(f"Ładowanie danych Quiz {detected_quiz}..."):
            extra_context = get_context_for_quiz(detected_quiz)

    full_content = f"{user_prompt}\n\nDODATKOWY KONTEKST DANYCH:\n{extra_context}" if extra_context else user_prompt

    with st.chat_message("assistant"):
        with st.spinner(f"Odpytywanie {selected_model}..."):
            try:
                headers = {
                    "Authorization": f"Bearer {api_key.strip()}",
                    "HTTP-Referer": "https://share.streamlit.io",
                    "X-Title": "TI-Weryfikator",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": selected_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": full_content}
                    ],
                    "temperature": 0.1
                }
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=90
                )
                if resp.status_code == 200:
                    ans = resp.json()["choices"][0]["message"]["content"]
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                else:
                    err = f"❌ Błąd OpenRouter ({resp.status_code}): {resp.text}"
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})
            except Exception as e:
                err = f"❌ Błąd zapytania: {e}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
