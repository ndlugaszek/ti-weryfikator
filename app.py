import os
import glob
import streamlit as st
import google.generativeai as genai
import pypdf

# Konfiguracja strony
st.set_page_config(
    page_title="TI Asystent - Weryfikacja Quizów",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Asystent Weryfikacji Zadań - Technologie Informacyjne")
st.caption("Model: Gemini 2.0 Flash + Code Execution | Baza: Arkusze, CSV, PDF-y kursowe")

# Pobranie klucza API (ze Secrets Hugging Face lub wpisanego ręcznie w sidebarze)
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Podaj klucz Gemini API:", type="password")

if not api_key:
    st.warning("⚠️ Brak klucza GEMINI_API_KEY. Wprowadź klucz w ustawieniach HF Space (Secrets) lub w panelu bocznym.")
    st.info("Darmowy klucz pobierzesz w 30 sekund na: https://aistudio.google.com/app/apikey")
    st.stop()

genai.configure(api_key=api_key)

# Ścieżki bazowe
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPA_PATH = os.path.join(BASE_DIR, "mapa-quizow.md")
INSTRUKCJA_PATH = os.path.join(BASE_DIR, "INSTRUKCJA.md")
CSV_DIR = os.path.join(BASE_DIR, "dane-csv")
MAT_DIR = os.path.join(BASE_DIR, "materialy")

@st.cache_data
def get_base_instructions():
    mapa = ""
    instrukcja = ""
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

ZASADY BEZWZGLĘDNE:
1. Odpowiadaj krótko i po polsku:
   Odpowiedź: [dokładny wynik/wartość]
   Ocena: poprawna / błędna / niejednoznaczna (jeśli podano propozycję użytkownika)
   Podstawa: [arkusz, komórki, strona PDF, formuła lub zarys obliczenia]
2. Zawsze weryfikuj obliczenia kodem Python (code execution). Nigdy nie zgaduj liczb w Excelu.
3. Zaokrąglenia i formatowanie: etykiety procentowe w wykresach kołowych Excela są domyślnie liczbami całkowitymi bez miejsc po przecinku (np. 32%, a nie 32.1%).
"""

# Panel boczny: wybór quizu
st.sidebar.header("Ustawienia Quizu")
quiz_choice = st.sidebar.selectbox(
    "Wybierz quiz do kontekstu:",
    ["Automatyczny (z treści pytania)", "Quiz 1", "Quiz 2", "Quiz 3", "Quiz 4", "Quiz 5", "Quiz 6", "Quiz 7"]
)

def extract_pdf_texts():
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

@st.cache_data
def load_all_materials():
    return extract_pdf_texts()

pdf_materials = load_all_materials()

def get_context_for_quiz(q_num):
    context_chunks = []
    
    # Dołączanie CSV dla quizów obliczeniowych
    if q_num == 2:
        for f in glob.glob(os.path.join(CSV_DIR, "Podrozni_23__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                context_chunks.append(f"Dane CSV dla {sheet}:\n{csv_f.read()}")
    elif q_num == 3:
        for f in glob.glob(os.path.join(CSV_DIR, "Ubezpiecznia-quiz_23__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                context_chunks.append(f"Dane CSV dla {sheet}:\n{csv_f.read()}")
    elif q_num == 4:
        for f in glob.glob(os.path.join(CSV_DIR, "04_Delegacje_quiz__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                context_chunks.append(f"Dane CSV dla {sheet}:\n{csv_f.read()}")
    elif q_num == 5:
        for f in glob.glob(os.path.join(CSV_DIR, "Dodatki_swiateczne_23__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                context_chunks.append(f"Dane CSV dla {sheet}:\n{csv_f.read()}")
    elif q_num in [1, 6, 7]:
        # Quizy teoretyczne: dołącz materiały PDF
        for fname, txt in pdf_materials.items():
            context_chunks.append(f"Materiał z {fname}:\n{txt[:40000]}") # bezpieczny fragment
            
    return "\n\n".join(context_chunks)

# Inicjalizacja historii czatu
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Obsługa pytania
user_prompt = st.chat_input("Wpisz pytanie (np. 'Quiz 4: oblicz średnią liczbę dni delegacji dla Warszawy')")
if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Detekcja quizu
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
        with st.spinner(f"Ładowanie danych dla Quiz {detected_quiz}..."):
            extra_context = get_context_for_quiz(detected_quiz)

    full_query = f"{user_prompt}\n\nDODATKOWY KONTEKST DANYCH:\n{extra_context}" if extra_context else user_prompt

    with st.chat_message("assistant"):
        with st.spinner("Przetwarzanie i weryfikacja kodem..."):
            try:
                model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    system_instruction=SYSTEM_PROMPT,
                    tools="code_execution"
                )
                response = model.generate_content(full_query)
                answer_text = response.text
                st.markdown(answer_text)
                st.session_state.messages.append({"role": "assistant", "content": answer_text})
            except Exception as e:
                err_msg = f"❌ Błąd zapytania AI: {e}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
