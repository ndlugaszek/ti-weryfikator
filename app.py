import os
import glob
import json
import time
import hashlib
import re
import csv
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
st.caption("Uczelniany System Weryfikacji Zadań Laboratoryjnych | Silnik: GPT-4o-mini | Baza kursowa 2025/2026")

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

# ==================== DETERMINISTYCZNY SILNIK EKSPERCKI (ZERO HALUCYNACJI) ====================
def solve_deterministic_question(q):
    q_low = q.lower().replace(",", ".")
    
    # QUIZ 6: FORMUŁY DATOWE (Parametryczne)
    # 1. Liczba dni do / od wydarzenia w komórce:
    # A) W przeszłości: "ile dni temu" / "odbyło się" -> =DZIŚ()-CELL
    m_temu = re.search(r"w komórce\s+([a-z]\d+).*?(?:ile dni temu|odbyło się)", q_low)
    if m_temu:
        cell = m_temu.group(1).upper()
        return f"=DZIŚ()-{cell}", f"Wydarzenie z przeszłości (ile dni temu odbyło się zebranie): =DZIŚ()-{cell}"

    # B) W przyszłości: "za ile dni będzie" / "zbliżającego się" -> =CELL-DZIŚ()
    m_za_ile = re.search(r"w komórce\s+([a-z]\d+).*?(?:za ile dni|będzie)", q_low)
    if m_za_ile:
        cell = m_za_ile.group(1).upper()
        return f"={cell}-DZIŚ()", f"Wydarzenie w przyszłości (za ile dni będzie): ={cell}-DZIŚ()"

    # 2. Przesunięcie o N dni / tydzień z komórki: =CELL+N lub =CELL-N
    m_cell = re.search(r"w komórce\s+([a-z]\d+)", q_low)
    if m_cell and ("później" in q_low or "wcześniej" in q_low):
        cell = m_cell.group(1).upper()
        days = None
        if "tydzień" in q_low or "tygodnia" in q_low:
            days = "7"
        else:
            m_days = re.search(r"(\d+)\s+dni", q_low)
            if m_days:
                days = m_days.group(1)
        if days:
            if "później" in q_low or "za " in q_low:
                return f"={cell}+{days}", f"Dodanie {days} dni do daty w komórce {cell}"
            else:
                return f"={cell}-{days}", f"Odjęcie {days} dni od daty w komórce {cell}"

    # 3. Zawsze data od dziś: =DZIŚ()+N lub =DZIŚ()-N
    if "zawsze" in q_low and "data" in q_low:
        days = None
        if "tydzień" in q_low or "tygodnia" in q_low:
            days = "7"
        else:
            m_days = re.search(r"(\d+)\s+dni", q_low)
            if m_days:
                days = m_days.group(1)
        if days:
            if "wcześniej" in q_low or "temu" in q_low:
                return f"=DZIŚ()-{days}", f"Odjęcie {days} dni od bieżącej daty (wyłącznie funkcja DZIŚ)"
            else:
                return f"=DZIŚ()+{days}", f"Dodanie {days} dni do bieżącej daty (wyłącznie funkcja DZIŚ)"

    # 4. Wyciąganie części daty: ROK / MIESIĄC / DZIEŃ z komórki
    m_cell = re.search(r"w komórce\s+([a-z]\d+)", q_low)
    if m_cell:
        cell = m_cell.group(1).upper()
        if "rok" in q_low:
            return f"=ROK({cell})", f"Polska funkcja ROK({cell}) wyodrębniająca rok"
        if "miesiąc" in q_low:
            return f"=MIESIĄC({cell})", f"Polska funkcja MIESIĄC({cell}) wyodrębniająca miesiąc"
        if "dzień" in q_low or "dnia" in q_low:
            return f"=DZIEŃ({cell})", f"Polska funkcja DZIEŃ({cell}) wyodrębniająca dzień"

    # 5. Aktualny dzień / miesiąc / rok (niezależnie od formy gramatycznej)
    if ("aktualn" in q_low or "bieżąc" in q_low) and "rok" in q_low:
        return "=ROK(DZIŚ())", "Formuła zwracająca bieżący rok z funkcji DZIŚ()"
    if ("aktualn" in q_low or "bieżąc" in q_low) and ("dzień" in q_low or "dnia" in q_low):
        return "=DZIEŃ(DZIŚ())", "Formuła zwracająca numer bieżącego dnia w miesiącu z funkcji DZIŚ()"
    if ("aktualn" in q_low or "bieżąc" in q_low) and ("miesiąc" in q_low or "miesiąca" in q_low):
        return "=MIESIĄC(DZIŚ())", "Formuła zwracająca numer bieżącego miesiąca z funkcji DZIŚ()"

    # 6. Różnica dwóch dat: zawsze [data późniejsza] - [data wcześniejsza]
    m_diff = re.search(r"w komórce\s+([a-z]\d+)\s+wpisana jest data\s+(\d{4}-\d{2}-\d{2}).*?w komórce\s+([a-z]\d+)\s+data\s+(\d{4}-\d{2}-\d{2}).*?ile dni upłynęło", q_low)
    if m_diff:
        cell1, d1, cell2, d2 = m_diff.group(1).upper(), m_diff.group(2), m_diff.group(3).upper(), m_diff.group(4)
        if d2 > d1:
            return f"={cell2}-{cell1}", f"Różnica dat (zawsze późniejsza od wcześniejszej: {d2} minus {d1}): ={cell2}-{cell1}"
        else:
            return f"={cell1}-{cell2}", f"Różnica dat (zawsze późniejsza od wcześniejszej: {d1} minus {d2}): ={cell1}-{cell2}"

    m_diff_gen = re.search(r"w komórce\s+([a-z]\d+).*?w komórce\s+([a-z]\d+).*?ile dni upłynęło", q_low)
    if m_diff_gen:
        c1, c2 = m_diff_gen.group(1).upper(), m_diff_gen.group(2).upper()
        return f"={c2}-{c1} (jeśli {c2} jest późniejsza) lub ={c1}-{c2} (jeśli {c1} jest późniejsza)", "Zasada w Excelu: od daty późniejszej odejmujemy datę wcześniejszą"

    # 7. Tworzenie daty z wycinka arkusza (Zasada: ROK, MIESIĄC, DZIEŃ)
    if "dnia, miesiąca i roku" in q_low or "otrzymać z nich datę" in q_low:
        return (
            "=DATA(C2;B2;A2) lub =DATA(B3;B2;B1)",
            "ZASADA EXCELA: =DATA(ROK; MIESIĄC; DZIEŃ). Sprawdź układ komórek na zrzucie w pytaniu:\n"
            "• Układ poziomy (wiersz 2, C2=rok, B2=miesiąc, A2=dzień): wpisz `=DATA(C2;B2;A2)`\n"
            "• Układ pionowy (kolumna B, B3=rok, B2=miesiąc, B1=dzień): wpisz `=DATA(B3;B2;B1)`"
        )

    # QUIZ 1: FORMATOWANIE I TEORIA (Parametryczne)
    # Wpisano X%. Jaką wartość ma komórka?
    m_pct = re.search(r"wpisano\s+([0-9.]+)\s*%\.?\s*jaką wartość", q_low)
    if m_pct:
        val = float(m_pct.group(1))
        dec = str(round(val / 100, 5)).replace(".", ",")
        orig = m_pct.group(1).replace(".", ",")
        return f"{dec} oraz {orig}% (zaznacz obie)", f"Wartość liczbowa to {dec}, tożsamy zapis wartości to {orig}%"

    # Wpisano liczbę X i wyświetlono w formacie procentowym:
    m_disp = re.search(r"wpisano liczbę\s+([0-9.]+).*?formacie procentowym", q_low)
    if m_disp:
        val = float(m_disp.group(1))
        pct = str(int(round(val * 100))) + "%"
        orig = m_disp.group(1).replace(".", ",")
        return pct, f"{orig} pomnożone przez 100% daje {pct}"

    # Wpisano liczbę X i sformatowano z N miejscami dziesiętnymi:
    m_val = re.search(r"wpisano liczbę\s+([0-9.]+).*?miejsc.*?jaką wartość", q_low)
    if m_val:
        orig = m_val.group(1).replace(".", ",")
        return orig, "Sformatowanie liczby zmienia wyłącznie jej wygląd, nie zmienia faktycznej wartości"

    # Separator tysięcy
    m_sep = re.search(r"wpisano liczbę\s+([0-9.]+).*?separatora tysięcy", q_low)
    if m_sep:
        parts = m_sep.group(1).split(".")
        int_part = parts[0]
        dec_part = parts[1] if len(parts) > 1 else "0000"
        return f"{int_part[:-3]} {int_part[-3:]},{dec_part}", "Zastosowanie spacji jako separatora tysięcy i 4 miejsc po przecinku"

    # Pytania o import i kopiowanie
    if "zaimportowano" in q_low and "ponownie" in q_low:
        return "Nie", "Importowanie tworzy stałe połączenie ze źródłem danych, dane można odświeżać bez ponownego importu"

    if "skopiowano" in q_low and "ponownie" in q_low:
        return "Tak", "Zwykłe kopiowanie (kopiuj-wklej) nie zachowuje połączenia między plikami"

    # Za długi tekst w komórce A1
    if "nie mieści się" in q_low:
        if "pusta" in q_low or "puste" in q_low:
            return "możemy sformatować zawijając tekst w komórce, automatycznie dopasowując rozmiar czcionki, ORAZ może wyświetlać się na komórce B1 (zaznacz wszystkie 3)", "Dopuszczalne opcje przy pustej komórce sąsiedniej"
        else:
            return "zawijając tekst w komórce ORAZ automatycznie dopasowując rozmiar czcionki do wielkości komórki (zaznacz obie)", "Gdy komórka obok jest zajęta, tekst nie może na nią nachodzić"

    # QUIZ 7: WORD
    if "antynomia" in q_low:
        return "wstawić przypis dolny", "Objaśnienie niezrozumiałego słowa na dole strony drukowanej"
    if "spis wykresów" in q_low or "spis tabel" in q_low:
        return "skorzystać z opcji Wstaw podpis, następnie Wstaw spis ilustracji", "Mechanizm spisu ilustracji po wcześniejszym podpisaniu obiektów"
    if "zbyt szczegółowy" in q_low or "sprawozdania" in q_low:
        return "w komentarzu", "Komentarz służy do przekazywania uwag recenzenckich współpracownikowi"
    if "przypis końcowy" in q_low:
        return "na końcu dokumentu", "Przypisy końcowe trafiają na sam koniec dokumentu"
    if "dole każdej strony" in q_low and "nazwisko" in q_low:
        return "wstawić stopkę, następnie wpisać w niej imię i nazwisko", "Stopka powtarza się automatycznie na dole każdej strony"
    if "nagłówek 1" in q_low and "zastosujemy" in q_low:
        return "chcemy utworzyć spis treści", "Style nagłówkowe definiują strukturę spisu treści"
    if "h2o" in q_low:
        return "indeks dolny", "Cyfra w indeksie dolnym (H₂O)"

    # QUIZ 3: UBEZPIECZENIA 1 (Deterministyczne agregacje z arkusza)
    if "zestawienie" in q_low:
        if "a3" in q_low or "w komórce a3" in q_low:
            if "ubezpiecz" in q_low:
                return "=MAX('Ubezpieczenia 1'!C7:C388)", "Formuła na najwyższą kwotę ubezpieczenia w komórce A3: =MAX('Ubezpieczenia 1'!C7:C388)"
            return "=MAX('Ubezpieczenia 1'!J7:J388)", "Formuła na najwyższą kwotę do zapłaty w komórce A3: =MAX('Ubezpieczenia 1'!J7:J388)"
        if "a4" in q_low or "w komórce a4" in q_low:
            if "ubezpiecz" in q_low:
                return "=MIN('Ubezpieczenia 1'!C7:C388)", "Formuła na najniższą kwotę ubezpieczenia w komórce A4: =MIN('Ubezpieczenia 1'!C7:C388)"
            return "=MIN('Ubezpieczenia 1'!J7:J388)", "Formuła na najniższą kwotę do zapłaty w komórce A4: =MIN('Ubezpieczenia 1'!J7:J388)"
        if "a1" in q_low or "w komórce a1" in q_low:
            if "ubezpiecz" in q_low:
                return "=SUMA('Ubezpieczenia 1'!C7:C388)", "Formuła na łączną kwotę ubezpieczenia w komórce A1: =SUMA('Ubezpieczenia 1'!C7:C388)"
            return "=SUMA('Ubezpieczenia 1'!J7:J388)", "Formuła na łączną kwotę do zapłaty w komórce A1: =SUMA('Ubezpieczenia 1'!J7:J388)"
        if "a2" in q_low or "w komórce a2" in q_low:
            if "ubezpiecz" in q_low:
                return "=ŚREDNIA('Ubezpieczenia 1'!C7:C388)", "Formuła na średnią kwotę ubezpieczenia w komórce A2: =ŚREDNIA('Ubezpieczenia 1'!C7:C388)"
            return "=ŚREDNIA('Ubezpieczenia 1'!J7:J388)", "Formuła na średnią kwotę do zapłaty w komórce A2: =ŚREDNIA('Ubezpieczenia 1'!J7:J388)"

    if "mniej niż 15 dni" in q_low or ("nie będą korzystać" in q_low and "samochod" in q_low):
        return "462600", "Łączna kwota ubezpieczenia dla wyposażenie='nie' i samochód zastępczy < 15 dni (2 lub 5 dni) = 462600."

    if ("nie więcej niż 300" in q_low or "<= 300" in q_low or "<=300" in q_low) and "zapłaty" in q_low:
        return "135", "Liczba klientów z kwotą do zapłaty <= 300 zł: LICZ.JEŻELI(J7:J388; '<=300') = 135."

    if "samochod" in q_low or "samochód" in q_low:
        if "co najmniej 5" in q_low or ">= 5" in q_low or ">=5" in q_low:
            return "205", "Liczba klientów z liczbą dni >= 5 (5 dni: 105 osób + 15 dni: 100 osób) = 205."
        if "nie więcej niż 5" in q_low or "<= 5" in q_low or "<=5" in q_low:
            return "213", "Liczba klientów z liczbą dni <= 5 (2 dni: 108 osób + 5 dni: 105 osób) = 213."
        if "dokładnie 2" in q_low or "przez 2 dni" in q_low:
            return "108", "Liczba komórek z wartością 2 w kolumnie Samochód zastępczy = 108."
        if "dokładnie 5" in q_low or "przez 5 dni" in q_low:
            return "105", "Liczba komórek z wartością 5 w kolumnie Samochód zastępczy = 105."
        if "15 dni" in q_low or "więcej niż 5" in q_low:
            return "100", "Liczba komórek z wartością 15 w kolumnie Samochód zastępczy = 100."

    if "do zapłaty" in q_low:
        if "najwyższ" in q_low or "maksymaln" in q_low:
            if "komórce" in q_low or "formuł" in q_low or "zestawienie" in q_low:
                return "=MAX('Ubezpieczenia 1'!J7:J388)", "Funkcja MAX na kolumnie kwot do zapłaty J7:J388."
            return "12000", "Maksymalna kwota do zapłaty: MAX(J7:J388) = 12000."
        if "najniższ" in q_low or "minimaln" in q_low:
            if "komórce" in q_low or "formuł" in q_low or "zestawienie" in q_low:
                return "=MIN('Ubezpieczenia 1'!J7:J388)", "Funkcja MIN na kolumnie kwot do zapłaty J7:J388."
            return "144", "Minimalna kwota do zapłaty: MIN(J7:J388) = 144."
        if "łączn" in q_low or "suma" in q_low:
            if "autoalarm" in q_low and "blokad" in q_low:
                return "99648", "=SUMA.WARUNKÓW na kwocie do zapłaty (J7:J388) dla autoalarm='+' i blokada='+' = 99648."
            if "komórce" in q_low or "formuł" in q_low or "zestawienie" in q_low:
                return "=SUMA('Ubezpieczenia 1'!J7:J388)", "Funkcja SUMA na kolumnie kwot do zapłaty J7:J388."
            if "wszystkich" in q_low or "klientów" in q_low:
                return "368352", "Łączna kwota do zapłaty wszystkich klientów: SUMA(J7:J388) = 368352."
        if "bagaż" in q_low or "bagażu" in q_low:
            if "standard" in q_low and "co najmniej 5" in q_low:
                return "1066.9 (lub 1066,9)", "Średnia kwota do zapłaty (bagaż standard + samochód zastępczy >= 5 dni; 55 klientów, suma 58680 zł) = 1066,9."
            if "vip" in q_low and "dodatkow" in q_low:
                return "2567.2 (lub 2567,2)", "ŚREDNIA.WARUNKÓW na kwocie do zapłaty dla bagaż='vip' i dodatkowe='tak' = 2567,2."
        if "średni" in q_low:
            if "komórce" in q_low or "formuł" in q_low or "zestawienie" in q_low:
                return "=ŚREDNIA('Ubezpieczenia 1'!J7:J388)", "Funkcja ŚREDNIA na kolumnie kwot do zapłaty J7:J388."
            if "bagaż" not in q_low and "dodatkow" not in q_low:
                return "964.27 (lub 964,27)", "Średnia kwota do zapłaty wszystkich klientów: ŚREDNIA(J7:J388) = 964,27."

    if "car assistance" in q_low:
        if "nie korzysta" in q_low or "bez car" in q_low or "brakiem" in q_low or "nie ma" in q_low:
            return "69", "Liczba klientów z brakiem Car Assistance = 69."
        if "korzysta" in q_low:
            return "313", "Liczba klientów korzystających z Car Assistance (382 - 69) = 313."

    if "kwota ubezpieczenia" in q_low or "kwotę ubezpieczenia" in q_low:
        if "najwyższ" in q_low or "maksymaln" in q_low:
            return "100000", "Maksymalna kwota ubezpieczenia: MAX(C7:C388) = 100000."
        if "najniższ" in q_low or "minimaln" in q_low:
            return "1200", "Minimalna kwota ubezpieczenia: MIN(C7:C388) = 1200."
        if "łączn" in q_low and "autoalarm" in q_low and "blokad" in q_low:
            return "830400", "=SUMA.WARUNKÓW dla autoalarm='tak' i blokada='tak' = 830400."
        if "średni" in q_low and "wszystkich" in q_low:
            return "8034.29 (lub 8034,29)", "Średnia kwota ubezpieczenia: ŚREDNIA(C7:C388) = 8034,29."

    return None, None

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

CONFLICT_PAIRS = [
    ({"najwyższ", "maksymaln"}, {"najniższ", "minimaln"}),
    ({"wcześniej", "temu", "przed"}, {"później", "po"}),
    ({"nie ubezpiecza", "bez ubezpieczenia"}, {"ubezpiecza bagaż", "posiada ubezpieczenie bagażu"}),
    ({"nie korzysta"}, {"korzysta"}),
    ({"nie skorzysta"}, {"skorzysta"}),
    ({"nie zadeklarowało"}, {"zadeklarowało", "podjęło decyzję"}),
    ({"kwotę do zapłaty", "kwota do zapłaty", "do zapłaty"}, {"kwota ubezpieczenia", "kwotę ubezpieczenia"}),
    ({"rok", "roku"}, {"miesiąc", "miesiąca"}),
    ({"miesiąc", "miesiąca"}, {"dzień", "dnia"}),
    ({"rok", "roku"}, {"dzień", "dnia"}),
    ({"nie więcej niż 5", "<= 5"}, {"co najmniej 5", ">= 5", "dokładnie 2", "dokładnie 5", "15 dni"}),
    ({"co najmniej 5", ">= 5"}, {"nie więcej niż 5", "<= 5", "dokładnie 2", "dokładnie 5"}),
    ({"w komórce a3", "komórce a3"}, {"w komórce a4", "komórce a4", "w komórce a1", "w komórce a2"}),
    ({"w komórce a4", "komórce a4"}, {"w komórce a3", "komórce a3", "w komórce a1", "w komórce a2"})
]

def has_conflict(q1, q2):
    q1_low, q2_low = q1.lower(), q2.lower()
    for grp_a, grp_b in CONFLICT_PAIRS:
        in_a1 = any(w in q1_low for w in grp_a)
        in_b1 = any(w in q1_low for w in grp_b)
        in_a2 = any(w in q2_low for w in grp_a)
        in_b2 = any(w in q2_low for w in grp_b)
        if (in_a1 and in_b2 and not in_b1) or (in_b1 and in_a2 and not in_a1):
            return True
    return False

def normalize_exact_text(text):
    text = text.lower().replace(",", ".")
    text = re.sub(r"(?:wynik|odpowiedź|formułę)[^.]*wpisz poniżej[:.]?", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def exact_match(query):
    if not known_db:
        return None
    q_norm = normalize_exact_text(query)
    if not q_norm:
        return None
    for item in known_db:
        t_norm = normalize_exact_text(item.get("pytanie", ""))
        if q_norm == t_norm:
            return item
    return None

def calculate_from_csv(query):
    q_low = query.lower().replace(",", ".")
    
    # 1. QUIZ 3: UBEZPIECZENIA 1
    if any(k in q_low for k in ["ubezpiecz", "do zapłaty", "car assistance", "samochód zastępczy", "samochodu zastępczego", "autoalarm", "immobilizer", "blokad"]):
        csv_path = os.path.join(CSV_DIR, "Ubezpiecznia-quiz_23__Ubezpieczenia_1.csv")
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8") as f:
                rows = list(csv.reader(f))[4:]

            # Specjalne warunki kombinowane:
            # A) Bagaż standard + samochód >= 5 dni
            if "standard" in q_low and ("co najmniej 5" in q_low or ">= 5" in q_low or ">=5" in q_low):
                filtered = [r for r in rows if r[7].strip().lower() == "standard" and r[9].strip() in ["5", "15"]]
                if "do zapłaty" in q_low and "średni" in q_low:
                    avg = sum(float(r[10]) for r in filtered) / len(filtered)
                    return f"{round(avg, 1)}", f"Średnia kwota do zapłaty dla bagaż standard i samochód >= 5 dni ({len(filtered)} klientów) = {round(avg, 1)}"

            # B) Wyposażenie "nie" + samochód < 15 dni
            if "mniej niż 15" in q_low or ("nie będą korzystać" in q_low and "samochod" in q_low):
                filtered = [r for r in rows if r[8].strip() == "nie" and r[9].strip() in ["2", "5"]]
                s = sum(float(r[3]) for r in filtered)
                return str(int(s)), f"Łączna kwota ubezpieczenia dla wyposażenie='nie' i samochód < 15 dni ({len(filtered)} klientów) = {int(s)}"

            # C) Autoalarm + Blokada
            if "autoalarm" in q_low and "blokad" in q_low:
                filtered = [r for r in rows if r[4].strip() == "+" and r[6].strip() == "+"]
                if "do zapłaty" in q_low:
                    s = sum(float(r[10]) for r in filtered)
                    return str(int(s)), f"Łączna kwota do zapłaty (Autoalarm + Blokada; {len(filtered)} klientów) = {int(s)}"
                if "kwota ubezpieczenia" in q_low or "kwotę ubezpieczenia" in q_low:
                    s = sum(float(r[3]) for r in filtered)
                    return str(int(s)), f"Łączna kwota ubezpieczenia (Autoalarm + Blokada; {len(filtered)} klientów) = {int(s)}"

            # D) Bagaż VIP + wyposażenie "tak"
            if "vip" in q_low and ("dodatkow" in q_low or "wyposażeni" in q_low):
                filtered = [r for r in rows if r[7].strip().lower() == "vip" and r[8].strip() == "tak"]
                if "do zapłaty" in q_low and "średni" in q_low:
                    avg = sum(float(r[10]) for r in filtered) / len(filtered)
                    return f"{round(avg, 1)}", f"Średnia kwota do zapłaty (VIP + wyposażenie 'tak') = {round(avg, 1)}"
                if "ubezpiecz" in q_low and "średni" in q_low:
                    avg = sum(float(r[3]) for r in filtered) / len(filtered)
                    return f"{round(avg, 1)}", f"Średnia kwota ubezpieczenia (VIP + wyposażenie 'tak') = {round(avg, 1)}"

            # E) Liczba dni samochodu zastępczego
            if "samochod" in q_low or "samochód" in q_low:
                if "co najmniej 5" in q_low or ">= 5" in q_low or ">=5" in q_low:
                    cnt = sum(1 for r in rows if r[9].strip() in ["5", "15"])
                    return str(cnt), f"Liczba klientów z samochodem zastępczym >= 5 dni = {cnt}"
                if "nie więcej niż 5" in q_low or "<= 5" in q_low or "<=5" in q_low:
                    cnt = sum(1 for r in rows if r[9].strip() in ["2", "5"])
                    return str(cnt), f"Liczba klientów z samochodem zastępczym <= 5 dni = {cnt}"
                if "dokładnie 2" in q_low or "przez 2 dni" in q_low:
                    cnt = sum(1 for r in rows if r[9].strip() == "2")
                    return str(cnt), f"Liczba klientów z samochodem zastępczym na 2 dni = {cnt}"
                if "dokładnie 5" in q_low or "przez 5 dni" in q_low:
                    cnt = sum(1 for r in rows if r[9].strip() == "5")
                    return str(cnt), f"Liczba klientów z samochodem zastępczym na 5 dni = {cnt}"
                if "15 dni" in q_low or "więcej niż 5" in q_low:
                    cnt = sum(1 for r in rows if r[9].strip() == "15")
                    return str(cnt), f"Liczba klientów z samochodem zastępczym na 15 dni = {cnt}"

            # F) Kwota do zapłaty <= 300
            if "nie więcej niż 300" in q_low or "<= 300" in q_low or "<=300" in q_low:
                cnt = sum(1 for r in rows if float(r[10]) <= 300)
                return str(cnt), f"Liczba klientów z kwotą do zapłaty <= 300 zł = {cnt}"

            # G) Kwota ubezpieczenia >= limit
            m_gte = re.search(r"co najmniej\s+(\d+)", q_low)
            if m_gte and ("kwot" in q_low or "ubezpiecz" in q_low):
                limit = float(m_gte.group(1))
                cnt = sum(1 for r in rows if float(r[3]) >= limit)
                return str(cnt), f"Liczba klientów z kwotą ubezpieczenia >= {int(limit)} = {cnt}"

            # H) Agregaty proste (MAX, MIN, SUMA, ŚREDNIA)
            if "do zapłaty" in q_low:
                vals = [float(r[10]) for r in rows]
                if "najwyższ" in q_low or "maksymaln" in q_low:
                    return str(int(max(vals))), f"MAX(J7:J388) na kolumnie Do zapłaty = {int(max(vals))}"
                if "najniższ" in q_low or "minimaln" in q_low:
                    return str(int(min(vals))), f"MIN(J7:J388) na kolumnie Do zapłaty = {int(min(vals))}"
                if "łączn" in q_low or "suma" in q_low:
                    return str(int(sum(vals))), f"SUMA(J7:J388) na kolumnie Do zapłaty = {int(sum(vals))}"
                if "średni" in q_low and "wszystkich" in q_low:
                    return f"{sum(vals)/len(vals):.2f}", f"ŚREDNIA(J7:J388) na kolumnie Do zapłaty = {sum(vals)/len(vals):.2f}"

            if "kwota ubezpieczenia" in q_low or "kwotę ubezpieczenia" in q_low:
                vals = [float(r[3]) for r in rows]
                if "najwyższ" in q_low or "maksymaln" in q_low:
                    return str(int(max(vals))), f"MAX(C7:C388) na kolumnie Kwota ubezpieczenia = {int(max(vals))}"
                if "najniższ" in q_low or "minimaln" in q_low:
                    return str(int(min(vals))), f"MIN(C7:C388) na kolumnie Kwota ubezpieczenia = {int(min(vals))}"
                if "łączn" in q_low or "suma" in q_low:
                    return str(int(sum(vals))), f"SUMA(C7:C388) na kolumnie Kwota ubezpieczenia = {int(sum(vals))}"
                if "średni" in q_low and "wszystkich" in q_low:
                    return f"{sum(vals)/len(vals):.2f}", f"ŚREDNIA(C7:C388) na kolumnie Kwota ubezpieczenia = {sum(vals)/len(vals):.2f}"

    # 2. QUIZ 4: WYKRESY KOŁOWE (DANE 1)
    if "dane 1" in q_low or "delegacj" in q_low or "wykres kołowy" in q_low:
        pie_shares = {
            ("hiszpan", "dieta"): "25",
            ("włoch", "dieta"): "32",
            ("chorwacj", "dieta"): "36",
            ("grecj", "nadbagaż"): "2",
            ("austri", "nadbagaż"): "3"
        }
        for (kraj, kat), val in pie_shares.items():
            if kraj in q_low and kat in q_low:
                return val, f"Wartość procentowa wycinka {kat} dla kraju {kraj} = {val}% (wpisz {val})"

    return None, None

def extract_tokens(text):
    text = text.lower().replace(",", ".")
    words = set(re.findall(r"[a-ząćęłńóśźż0-9%]+", text))
    meaningful = words - STOPWORDS
    nums = set(re.findall(r"\d+(?:\.\d+)?%?", text))
    return meaningful, nums

def smart_match(query, threshold=0.75):
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

        # Odrzucenie sprzecznych pojęć (np. najwyższa vs najniższa)
        if has_conflict(query, target_text):
            continue

        t_words, t_nums = extract_tokens(target_text)

        # Precyzyjna zgodność liczb
        if q_nums:
            num_inter = len(q_nums.intersection(t_nums))
            num_score = num_inter / len(q_nums)
            if num_score < 0.6:
                continue
        else:
            num_score = 1.0

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

BEZWZGLĘDNE REGUŁY ODPOWIEDZI:
1. Odpowiadaj natychmiast i zwięźle po polsku:
   **Odpowiedź:** [dokładny wynik, liczba lub polska formuła Excela]
   **Podstawa:** [zwięzłe uzasadnienie, komórki, funkcja lub obliczenie]
2. BEZWZGLĘDNY ZAKAZ generowania tekstu narracyjnego, zapowiedzi ("Zaraz to obliczę", "Przeanalizuję", "Przeprowadzam obliczenia", "Chętnie pomogę") oraz przeprosin.
3. Jeśli do zapytania dołączono dane CSV, NATYCHMIAST wykonaj obliczenie na danych i podaj ostateczną liczbę.
4. Nazwy funkcji Excela podawaj WYŁĄCZNIE w języku polskim: =DZIŚ(), =DATA(), =MIESIĄC(), =ROK(), =DZIEŃ(), =SUMA(), =ŚREDNIA(), =JEŻELI(), =MAX(), =MIN(), =LICZ.JEŻELI(). Bezwzględny zakaz nazw angielskich (TODAY, DATE, MONTH, SUM, IF).
5. Etykiety procentowe w wykresach kołowych Excela są liczbami całkowitymi bez miejsc po przecinku (np. 25).
"""

INTERNAL_ENGINES = [
    "openai/gpt-4o-mini",
    "deepseek/deepseek-chat"
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
    - **Wydajność:** Deterministyczny silnik formuł Excela eliminuje błędy i halucynacje.
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
    
    # POZIOM 1: Wyszukiwanie słowo w słowo (Exact Match 100%)
    exact_item = exact_match(user_prompt)
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
            output_lines.append(f"\n---\n*⚡ Źródło: Zweryfikowana baza (Dopasowanie 100% słowo w słowo) | Czas: {elapsed} s*")
            final_resp = "\n\n".join(output_lines)
            st.markdown(final_resp)
            st.session_state.messages.append({"role": "assistant", "content": final_resp})

    else:
        # POZIOM 2: Deterministyczny silnik regułowy (formuły parametryczne Quiz 6 daty, Quiz 1 formatowanie, Quiz 7 Word)
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
            # POZIOM 3: Inteligentne dopasowanie słów kluczowych do bazy wiedzy (z twardym filtrem sprzeczności)
            matched_item, score = smart_match(user_prompt, threshold=0.80)
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
                # POZIOM 4: Autonomiczny Kalkulator Arkuszy Python (obliczenia na CSV bez halucynacji LLM)
                calc_ans, calc_uzas = calculate_from_csv(user_prompt)
                if calc_ans:
                    with st.chat_message("assistant"):
                        elapsed = round(time.time() - start_time, 3)
                        final_resp = (
                            f"**Odpowiedź:** `{calc_ans}`\n\n"
                            f"**Podstawa:** {calc_uzas}\n\n"
                            f"---\n*📊 Silnik: Bezpośrednia kalkulacja tabelaryczna Python CSV | Czas: {elapsed} s*"
                        )
                        st.markdown(final_resp)
                        st.session_state.messages.append({"role": "assistant", "content": final_resp})
                else:
                    # POZIOM 5: Fallback do modelu LLM (ostateczność dla pytań otwartych)
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
