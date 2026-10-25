import re

def solve_deterministic_question(q: str):
    q_low = q.lower().replace(",", ".")
    
    # QUIZ 6: FORMUŁY DATOWE (Parametryczne)
    # 1. Liczba dni do / od wydarzenia w komórce:
    m_temu = re.search(r"w komórce\s+([a-z]\d+).*?(?:ile dni temu|odbyło się)", q_low)
    if m_temu:
        cell = m_temu.group(1).upper()
        return f"=DZIŚ()-{cell}", f"Wydarzenie z przeszłości (ile dni temu odbyło się zebranie): =DZIŚ()-{cell}"

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

    # 5. Aktualny dzień / miesiąc / rok
    if ("aktualn" in q_low or "bieżąc" in q_low) and "rok" in q_low:
        return "=ROK(DZIŚ())", "Formuła zwracająca bieżący rok z funkcji DZIŚ()"
    if ("aktualn" in q_low or "bieżąc" in q_low) and ("dzień" in q_low or "dnia" in q_low):
        return "=DZIEŃ(DZIŚ())", "Formuła zwracająca numer bieżącego dnia w miesiącu z funkcji DZIŚ()"
    if ("aktualn" in q_low or "bieżąc" in q_low) and ("miesiąc" in q_low or "miesiąca" in q_low):
        return "=MIESIĄC(DZIŚ())", "Formuła zwracająca numer bieżącego miesiąca z funkcji DZIŚ()"

    # 6. Różnica dwóch dat
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

    # 7. Tworzenie daty z wycinka arkusza
    if "dnia, miesiąca i roku" in q_low or "otrzymać z nich datę" in q_low:
        return (
            "=DATA(C2;B2;A2) lub =DATA(B3;B2;B1)",
            "ZASADA EXCELA: =DATA(ROK; MIESIĄC; DZIEŃ). Sprawdź układ komórek na zrzucie w pytaniu:\n"
            "• Układ poziomy (wiersz 2, C2=rok, B2=miesiąc, A2=dzień): wpisz `=DATA(C2;B2;A2)`\n"
            "• Układ pionowy (kolumna B, B3=rok, B2=miesiąc, B1=dzień): wpisz `=DATA(B3;B2;B1)`"
        )

    # QUIZ 1: FORMATOWANIE I TEORIA (Parametryczne)
    m_pct = re.search(r"wpisano\s+([0-9.]+)\s*%\.?\s*jaką wartość", q_low)
    if m_pct:
        val = float(m_pct.group(1))
        dec = str(round(val / 100, 5)).replace(".", ",")
        orig = m_pct.group(1).replace(".", ",")
        return f"{dec} oraz {orig}% (zaznacz obie)", f"Wartość liczbowa to {dec}, tożsamy zapis wartości to {orig}%"

    m_disp = re.search(r"wpisano liczbę\s+([0-9.]+).*?formacie procentowym", q_low)
    if m_disp:
        val = float(m_disp.group(1))
        pct = str(int(round(val * 100))) + "%"
        orig = m_disp.group(1).replace(".", ",")
        return pct, f"{orig} pomnożone przez 100% daje {pct}"

    m_val = re.search(r"wpisano liczbę\s+([0-9.]+).*?miejsc.*?jaką wartość", q_low)
    if m_val:
        orig = m_val.group(1).replace(".", ",")
        return orig, "Sformatowanie liczby zmienia wyłącznie jej wygląd, nie zmienia faktycznej wartości"

    m_sep = re.search(r"wpisano liczbę\s+([0-9.]+).*?separatora tysięcy", q_low)
    if m_sep:
        parts = m_sep.group(1).split(".")
        int_part = parts[0]
        dec_part = parts[1] if len(parts) > 1 else "0000"
        return f"{int_part[:-3]} {int_part[-3:]},{dec_part}", "Zastosowanie spacji jako separatora tysięcy i 4 miejsc po przecinku"

    if "zaimportowano" in q_low and "ponownie" in q_low:
        return "Nie", "Importowanie tworzy stałe połączenie ze źródłem danych, dane można odświeżać bez ponownego importu"

    if "skopiowano" in q_low and "ponownie" in q_low:
        return "Tak", "Zwykłe kopiowanie (kopiuj-wklej) nie zachowuje połączenia między plikami"

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

    # QUIZ 3: UBEZPIECZENIA 1 (Statyczne formuły i stałe agregaty)
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
