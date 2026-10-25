import os
import glob
import json
import time
import hashlib
import csv
import streamlit as st
import pypdf

from core.rules import solve_deterministic_question
from core.search import SearchIndex
from core.calc import calculate_from_csv
from core.llm import stream_openrouter_completion, FREE_MODELS

# Konfiguracja strony
st.set_page_config(
    page_title="Asystent Weryfikacji Zadań TI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ścieżki bazowe
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPA_PATH = os.path.join(BASE_DIR, "mapa-quizow.md")
INSTRUKCJA_PATH = os.path.join(BASE_DIR, "INSTRUKCJA.md")
BAZA_WIEDZY_PATH = os.path.join(BASE_DIR, "baza_wiedzy.json")
CSV_DIR = os.path.join(BASE_DIR, "dane-csv")
MAT_DIR = os.path.join(BASE_DIR, "materialy")

# Konfiguracja hasła i sesji
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
        st.query_params.clear()
    else:
        st.session_state.authenticated = False

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
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error("❌ Błędny klucz dostępu. Skontaktuj się ze starostą grupy.")
        st.markdown("---")
        st.caption("🔒 **Polityka prywatności:** Sesja jest anonimowa. System nie przetwarza danych osobowych ani numerów albumu.")
    st.stop()

# Główny nagłówek
st.title("🎓 Asystent Weryfikacji Zadań - Technologie Informacyjne")
st.caption("Uczelniany System Weryfikacji Zadań Laboratoryjnych | Baza kursowa 2025/2026 | Silnik Zoptymalizowany O(1)")

# Klucz OpenRouter
api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
    except Exception:
        pass

# ==================== PAMIĘĆ PODRĘCZNA (ST.CACHE) ====================
@st.cache_resource
def get_search_index():
    if os.path.exists(BAZA_WIEDZY_PATH):
        try:
            with open(BAZA_WIEDZY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return SearchIndex(data)
        except Exception:
            return SearchIndex([])
    return SearchIndex([])

search_index = get_search_index()

@st.cache_resource
def load_all_csv_tables():
    cache = {}
    if os.path.exists(CSV_DIR):
        for f in glob.glob(os.path.join(CSV_DIR, "*.csv")):
            fname = os.path.basename(f)
            try:
                with open(f, "r", encoding="utf-8") as csv_f:
                    cache[fname] = list(csv.reader(csv_f))
            except Exception:
                continue
    return cache

csv_tables = load_all_csv_tables()

@st.cache_resource
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

BEZWZGLĘDNE REGUŁY ODPOWIEDZI:
1. Odpowiadaj natychmiast i zwięźle po polsku:
   **Odpowiedź:** [dokładny wynik, liczba lub polska formuła Excela]
   **Podstawa:** [zwięzłe uzasadnienie, komórki, funkcja lub obliczenie]
2. BEZWZGLĘDNY ZAKAZ generowania tekstu narracyjnego, zapowiedzi ("Zaraz to obliczę", "Przeanalizuję", "Przeprowadzam obliczenia", "Chętnie pomogę") oraz przeprosin.
3. Jeśli do zapytania dołączono dane CSV, NATYCHMIAST wykonaj obliczenie na danych i podaj ostateczną liczbę.
4. Nazwy funkcji Excela podawaj WYŁĄCZNIE w języku polskim: =DZIŚ(), =DATA(), =MIESIĄC(), =ROK(), =DZIEŃ(), =SUMA(), =ŚREDNIA(), =JEŻELI(), =MAX(), =MIN(), =LICZ.JEŻELI(). Bezwzględny zakaz nazw angielskich (TODAY, DATE, MONTH, SUM, IF).
5. Etykiety procentowe w wykresach kołowych Excela są liczbami całkowitymi bez miejsc po przecinku (np. 25).
"""

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
    st.rerun()

def get_context_for_quiz(q_num: int) -> str:
    chunks = []
    prefix_map = {
        2: "Podrozni_23__",
        3: "Ubezpiecznia-quiz_23__",
        4: "04_Delegacje_quiz__",
        5: "Dodatki_swiateczne_23__"
    }
    if q_num in prefix_map:
        pref = prefix_map[q_num]
        for fname, rows in csv_tables.items():
            if fname.startswith(pref):
                sheet = fname.replace(".csv", "")
                sample = "\n".join([",".join(r) for r in rows[:60]])
                chunks.append(f"Dane tabelaryczne ({sheet}) [pierwsze 60 wierszy]:\n{sample}")
    elif q_num in [1, 6, 7]:
        for fname, txt in pdf_materials.items():
            chunks.append(f"Materiał dydaktyczny ({fname}):\n{txt[:15000]}")
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
    
    # POZIOM 1: Wyszukiwanie słowo w słowo O(1) Hash Map
    exact_item = search_index.exact_match(user_prompt)
    if exact_item:
        with st.chat_message("assistant"):
            elapsed = round(time.time() - start_time, 3)
            odp = exact_item.get("odpowiedz", "")
            form = exact_item.get("formula", "")
            uzas = exact_item.get("uzasadnienie", "")
            quiz_nr = exact_item.get("quiz", "Baza wiedzy")
            
            output_lines = [f"**Odpowiedź:** `{odp}`"]
            if form:
                output_lines.append(f"**Formuła:** `{form}`")
            if uzas:
                output_lines.append(f"**Podstawa:** {uzas}")
            output_lines.append(f"\n---\n*⚡ Źródło: Zweryfikowana baza (Dopasowanie O(1) 100%) | Czas: {elapsed} s*")
            final_resp = "\n\n".join(output_lines)
            st.markdown(final_resp)
            st.session_state.messages.append({"role": "assistant", "content": final_resp})

    else:
        # POZIOM 2: Deterministyczny silnik regułowy
        det_ans, det_uzas = solve_deterministic_question(user_prompt)
        if det_ans:
            with st.chat_message("assistant"):
                elapsed = round(time.time() - start_time, 3)
                final_resp = (
                    f"**Odpowiedź:** `{det_ans}`\n\n"
                    f"**Podstawa:** {det_uzas}\n\n"
                    f"---\n*⚡ Silnik: Deterministyczny regułowy (100% precyzji) | Czas: {elapsed} s*"
                )
                st.markdown(final_resp)
                st.session_state.messages.append({"role": "assistant", "content": final_resp})
        else:
            # POZIOM 3: Smart Match
            matched_item, score = search_index.smart_match(user_prompt, threshold=0.80)
            if matched_item and score >= 0.80:
                with st.chat_message("assistant"):
                    elapsed = round(time.time() - start_time, 2)
                    odp = matched_item.get("odpowiedz", "")
                    form = matched_item.get("formula", "")
                    uzas = matched_item.get("uzasadnienie", "")
                    quiz_nr = matched_item.get("quiz", "Baza wiedzy")
                    
                    output_lines = [f"**Odpowiedź:** `{odp}`"]
                    if form:
                        output_lines.append(f"**Formuła:** `{form}`")
                    if uzas:
                        output_lines.append(f"**Podstawa:** {uzas}")
                    output_lines.append(f"\n---\n*⚡ Źródło: Podobne zadanie w bazie ({quiz_nr}) | Trafność: {round(score*100)}% | Czas: {elapsed} s*")
                    final_resp = "\n\n".join(output_lines)
                    st.markdown(final_resp)
                    st.session_state.messages.append({"role": "assistant", "content": final_resp})
            else:
                # POZIOM 4: Kalkulator CSV w pamięci RAM
                calc_ans, calc_uzas = calculate_from_csv(user_prompt, csv_tables)
                if calc_ans:
                    with st.chat_message("assistant"):
                        elapsed = round(time.time() - start_time, 3)
                        final_resp = (
                            f"**Odpowiedź:** `{calc_ans}`\n\n"
                            f"**Podstawa:** {calc_uzas}\n\n"
                            f"---\n*📊 Silnik: Bezpośrednia kalkulacja w RAM | Czas: {elapsed} s*"
                        )
                        st.markdown(final_resp)
                        st.session_state.messages.append({"role": "assistant", "content": final_resp})
                else:
                    # POZIOM 5: Fallback LLM OpenRouter ze streamingiem
                    detected_quiz = None
                    if "Quiz 1" in quiz_choice: detected_quiz = 1
                    elif "Quiz 2" in quiz_choice: detected_quiz = 2
                    elif "Quiz 3" in quiz_choice: detected_quiz = 3
                    elif "Quiz 4" in quiz_choice: detected_quiz = 4
                    elif "Quiz 5" in quiz_choice: detected_quiz = 5
                    elif "Quiz 6" in quiz_choice: detected_quiz = 6
                    elif "Quiz 7" in quiz_choice: detected_quiz = 7
                    else:
                        q_low = user_prompt.lower()
                        for q in [1, 2, 3, 4, 5, 6, 7]:
                            if f"quiz {q}" in q_low or f"quiz{q}" in q_low or f"q{q}" in q_low:
                                detected_quiz = q
                                break
                        if not detected_quiz:
                            if any(w in q_low for w in ["ubezpiecz", "car assistance", "samochód zastępczy", "samochodu zastępczego", "autoalarm", "immobilizer", "blokad", "do zapłaty"]):
                                detected_quiz = 3
                            elif any(w in q_low for w in ["delegacj", "dieta", "nadbagaż", "kraj docelowy", "tabela przestawna", "wykres przestawny", "hiszpan", "grecj", "włoch", "austri", "turcj"]):
                                detected_quiz = 4
                            elif any(w in q_low for w in ["dodatk", "świątecz", "staż", "dział", "noworoczn", "prezent"]):
                                detected_quiz = 5
                            elif any(w in q_low for w in ["podróżn", "podrozn", "skala kolorów", "zestaw ikon"]):
                                detected_quiz = 2
                            elif any(w in q_low for w in ["data", "dni wcześniej", "dni później", "ile dni", "zebranie", "zakończenie projektu", "aktualny rok", "aktualnego miesiąca", "aktualnego dnia"]):
                                detected_quiz = 6
                            elif any(w in q_low for w in ["przypis", "recenzencka", "podpisów", "objaśnienie słowa", "h2o", "stopk"]):
                                detected_quiz = 7
                            elif any(w in q_low for w in ["wpisano", "format procentowy", "separator tysięcy", "access", "xml"]):
                                detected_quiz = 1

                    extra_context = ""
                    if detected_quiz:
                        with st.spinner(f"Pobieranie kontekstu Quiz {detected_quiz}..."):
                            extra_context = get_context_for_quiz(detected_quiz)

                    full_content = f"{user_prompt}\n\nKONTEKST DANYCH ŹRÓDŁOWYCH:\n{extra_context}" if extra_context else user_prompt

                    with st.chat_message("assistant"):
                        answer_obtained = False
                        last_error = ""

                        if not api_key:
                            st.error("Brak klucza OPENROUTER_API_KEY w konfiguracji środowiska.")
                        else:
                            for model_candidate in FREE_MODELS:
                                try:
                                    generator, used_model = stream_openrouter_completion(
                                        prompt=full_content,
                                        system_prompt=SYSTEM_PROMPT,
                                        api_key=api_key,
                                        model=model_candidate
                                    )
                                    response_placeholder = st.empty()
                                    collected_chunks = []
                                    for delta in generator:
                                        collected_chunks.append(delta)
                                        response_placeholder.markdown("".join(collected_chunks) + "▌")
                                    
                                    elapsed = round(time.time() - start_time, 2)
                                    final_text = "".join(collected_chunks)
                                    final_text_meta = f"{final_text}\n\n---\n*⏱️ Model: `{used_model}` | Czas: {elapsed} s*"
                                    response_placeholder.markdown(final_text_meta)
                                    st.session_state.messages.append({"role": "assistant", "content": final_text_meta})
                                    answer_obtained = True
                                    break
                                except Exception as e:
                                    last_error = str(e)

                            if not answer_obtained:
                                err_msg = (
                                    "⚠️ **Chwilowa niedostępność modeli darmowych OpenRouter.**\n\n"
                                    "Zalecenie: Odczekaj chwilę lub zadaj pytanie zawierające dokładne słowa kluczowe z arkusza.\n\n"
                                    f"*Szczegóły: {last_error}*"
                                )
                                st.error(err_msg)
                                st.session_state.messages.append({"role": "assistant", "content": err_msg})
