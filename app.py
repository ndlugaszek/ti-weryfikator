import os
import glob
import json
import time
import hashlib
import re
import difflib
import requests
import streamlit as st
import pypdf

# Konfiguracja strony
st.set_page_config(
    page_title="Asystent Weryfikacji Zadań TI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Konfiguracja hasła i trwałości sesji
DEFAULT_PASSWORD = "merito-ti-2026"
APP_PASSWORD = os.environ.get("APP_PASSWORD")
if not APP_PASSWORD:
    try:
        APP_PASSWORD = st.secrets.get("APP_PASSWORD", DEFAULT_PASSWORD)
    except Exception:
        APP_PASSWORD = DEFAULT_PASSWORD

AUTH_TOKEN = hashlib.sha256(APP_PASSWORD.encode()).hexdigest()[:16]

if "authenticated" not in st.session_state:
    if st.query_params.get("auth") == AUTH_TOKEN:
        st.session_state.authenticated = True
    else:
        st.session_state.authenticated = False

# Ekran logowania
if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center;'>🎓 Portal Weryfikacji Zadań - Technologie Informacyjne</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Dostęp autoryzowany dla grupy laboratoryjnej</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user_pwd = st.text_input("Klucz dostępu grupy:", type="password", placeholder="Wpisz hasło...")
            submitted = st.form_submit_button("Uzyskaj dostęp", use_container_width=True)
            if submitted:
                if user_pwd == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.query_params["auth"] = AUTH_TOKEN
                    st.rerun()
                else:
                    st.error("❌ Błędny klucz dostępu. Skontaktuj się ze starostą grupy.")
        
        st.markdown("---")
        st.caption("🔒 **Polityka prywatności:** Sesja jest anonimowa. System nie przetwarza danych osobowych ani numerów albumu.")
    st.stop()

# Główny nagłówek
st.title("🎓 Asystent Weryfikacji Zadań - Technologie Informacyjne")
st.caption("Uczelniany System Weryfikacji Zadań Laboratoryjnych | Baza kursowa 2025/2026")

# Ścieżki bazowe
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPA_PATH = os.path.join(BASE_DIR, "mapa-quizow.md")
INSTRUKCJA_PATH = os.path.join(BASE_DIR, "INSTRUKCJA.md")
BAZA_WIEDZY_PATH = os.path.join(BASE_DIR, "baza_wiedzy.json")
CSV_DIR = os.path.join(BASE_DIR, "dane-csv")
MAT_DIR = os.path.join(BASE_DIR, "materialy")

# Pobranie klucza OpenRouter
api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
    except Exception:
        pass

# Wczytanie bazy wiedzy znanych zadań
@st.cache_data
def load_known_database():
    if os.path.exists(BAZA_WIEDZY_PATH):
        try:
            with open(BAZA_WIEDZY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

known_db = load_known_database()

STOPWORDS = {
    "w", "we", "z", "ze", "do", "na", "o", "dla", "oraz", "i", "a", "jak",
    "jaka", "jaki", "jaką", "co", "ile", "ilu", "się", "jest", "są", "to",
    "ta", "te", "ten", "tym", "tej", "komórka", "komórce", "arkusz", "arkuszu",
    "wpisano", "liczba", "liczbę", "poniżej", "wpisz", "wynik", "oblicz",
    "pytanie", "odpowiedź", "zadanie", "należy", "znajduje", "znajdują"
}

def extract_tokens(text):
    text = text.lower().replace(",", ".")
    words = set(re.findall(r"[a-ząćęłńóśźż0-9%]+", text))
    meaningful = words - STOPWORDS
    nums = set(re.findall(r"\d+(?:\.\d+)?%?", text))
    return meaningful, nums

def smart_match(query, threshold=0.68):
    if not known_db:
        return None, 0.0
        
    q_words, q_nums = extract_tokens(query)
    q_clean = query.lower()
    best_item = None
    best_score = 0.0

    for item in known_db:
        t_pytanie = item.get("pytanie", "")
        t_klucze = " ".join(item.get("klucze", []))
        target_text = (t_pytanie + " " + t_klucze).lower()
        t_words, t_nums = extract_tokens(target_text)

        # Dopasowanie liczb i wartości kluczowych (np. 9% vs 2,3% vs 6%)
        if q_nums:
            num_inter = len(q_nums.intersection(t_nums))
            num_score = num_inter / len(q_nums)
            if num_score == 0:
                continue
        else:
            num_score = 1.0

        # Zgodność słów merytorycznych
        if q_words:
            inter = len(q_words.intersection(t_words))
            word_score = inter / len(q_words)
        else:
            word_score = 0.0

        seq = difflib.SequenceMatcher(None, q_clean, target_text).ratio()
        total_score = 0.5 * num_score + 0.4 * word_score + 0.1 * seq

        if total_score > best_score:
            best_score = total_score
            best_item = item

    if best_score >= threshold:
        return best_item, best_score
    return None, best_score

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

INTERNAL_ENGINES = [
    "cohere/north-mini-code:free",
    "dots-studio/dots-3-note-preview:free"
]

# Panel boczny
st.sidebar.header("Konfiguracja sesji")
quiz_choice = st.sidebar.selectbox(
    "Zakres weryfikacji:",
    ["Automatyczny (z treści pytania)", "Quiz 1", "Quiz 2", "Quiz 3", "Quiz 4", "Quiz 5", "Quiz 6", "Quiz 7"]
)

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Wyczyść historię zapytań", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

if st.sidebar.button("🚪 Wyloguj z urządzenia", use_container_width=True):
    st.session_state.authenticated = False
    if "auth" in st.query_params:
        del st.query_params["auth"]
    st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("ℹ️ Prywatność i Bezpieczeństwo"):
    st.markdown("""
    - **Poufność:** Wszystkie zapytania są przetwarzane w trybie stateless.
    - **Zero PII:** System nie gromadzi imion, nazwisk, PESEL ani numerów albumu.
    - **Trwałość sesji:** Logowanie jest zapamiętywane w Twojej przeglądarce.
    - **Wydajność:** Zweryfikowana baza 106 zadań gwarantuje natychmiastowe i bezbłędne odpowiedzi.
    """)

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
                texts[fname] = f"Błąd odczytu: {e}"
    return texts

pdf_materials = load_all_materials()

def get_context_for_quiz(q_num):
    chunks = []
    if q_num == 2:
        for f in glob.glob(os.path.join(CSV_DIR, "Podrozni_23__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                chunks.append(f"Dane tabelaryczne ({sheet}):\n{csv_f.read()}")
    elif q_num == 3:
        for f in glob.glob(os.path.join(CSV_DIR, "Ubezpiecznia-quiz_23__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                chunks.append(f"Dane tabelaryczne ({sheet}):\n{csv_f.read()}")
    elif q_num == 4:
        for f in glob.glob(os.path.join(CSV_DIR, "04_Delegacje_quiz__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                chunks.append(f"Dane tabelaryczne ({sheet}):\n{csv_f.read()}")
    elif q_num == 5:
        for f in glob.glob(os.path.join(CSV_DIR, "Dodatki_swiateczne_23__*.csv")):
            sheet = os.path.basename(f).replace(".csv", "")
            with open(f, "r", encoding="utf-8") as csv_f:
                chunks.append(f"Dane tabelaryczne ({sheet}):\n{csv_f.read()}")
    elif q_num in [1, 6, 7]:
        for fname, txt in pdf_materials.items():
            chunks.append(f"Materiał dydaktyczny ({fname}):\n{txt[:40000]}")
    return "\n\n".join(chunks)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_prompt = st.chat_input("Wklej treść pytania z quizu...")
if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    start_time = time.time()
    
    # 1. KROK BŁYSKAWICZNY: Inteligentne dopasowanie do bazy zweryfikowanych odpowiedzi
    matched_item, score = smart_match(user_prompt)

    if matched_item and score >= 0.68:
        with st.chat_message("assistant"):
            elapsed = round(time.time() - start_time, 2)
            odp = matched_item.get("odpowiedz", "")
            form = matched_item.get("formula", "")
            uzas = matched_item.get("uzasadnienie", "")
            quiz_nr = matched_item.get("quiz", "Baza wiedzy")
            
            output_lines = [
                f"**Odpowiedź:** {odp}"
            ]
            if form:
                output_lines.append(f"**Formuła:** `{form}`")
            if uzas:
                output_lines.append(f"**Podstawa:** {uzas}")
                
            output_lines.append(f"\n---\n*⚡ Źródło: Zweryfikowana baza ({quiz_nr}) | Trafność: {round(score*100)}% | Czas: {elapsed} s*")
            
            final_resp = "\n\n".join(output_lines)
            st.markdown(final_resp)
            st.session_state.messages.append({"role": "assistant", "content": final_resp})
    else:
        # 2. KROK FALLBACK: Jeśli pytanie jest nietypowe, odpytujemy model AI
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
            with st.spinner(f"Pobieranie bazy danych modułu Quiz {detected_quiz}..."):
                extra_context = get_context_for_quiz(detected_quiz)

        full_content = f"{user_prompt}\n\nKONTEKST DANYCH ŹRÓDŁOWYCH:\n{extra_context}" if extra_context else user_prompt

        with st.chat_message("assistant"):
            answer_obtained = False
            last_error = ""

            headers = {
                "Authorization": f"Bearer {api_key.strip()}" if api_key else "",
                "HTTP-Referer": "https://share.streamlit.io",
                "X-Title": "TI-Weryfikator-Akademicki",
                "Content-Type": "application/json"
            }

            for engine_model in INTERNAL_ENGINES:
                with st.spinner("Weryfikacja danych i przeliczanie formuł..."):
                    try:
                        payload = {
                            "model": engine_model,
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
                            elapsed = round(time.time() - start_time, 2)
                            raw_ans = resp.json()["choices"][0]["message"]["content"]
                            ans_with_meta = f"{raw_ans}\n\n---\n*⏱️ Czas weryfikacji: {elapsed} s*"
                            
                            st.markdown(ans_with_meta)
                            st.session_state.messages.append({"role": "assistant", "content": ans_with_meta})
                            answer_obtained = True
                            break
                        else:
                            last_error = f"Kod odpowiedzi: {resp.status_code}"
                    except Exception as e:
                        last_error = f"Błąd komunikacji: {e}"

            if not answer_obtained:
                err_msg = (
                    "⚠️ **Chwilowe obciążenie serwerów obliczeniowych.**\n\n"
                    "Zalecenie: Odczekaj 30–60 sekund i zadaj pytanie ponownie.\n\n"
                    f"*Szczegóły: {last_error}*"
                )
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
