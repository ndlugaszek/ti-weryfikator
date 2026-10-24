# Mapa quizów i arkuszy

| Quiz | Arkusz XLSX | Arkusze w pliku |
|---|---|---|
| Quiz 1 | brak | – |
| Quiz 2 | arkusze/Podrozni_23.xlsx | Podróżni_1 … Podróżni_13 |
| Quiz 3 | arkusze/Ubezpiecznia-quiz_23.xlsx | Ubezpieczenia 1, Zestawienie |
| Quiz 4 | arkusze/04_Delegacje_quiz.xlsx | Dane 1, Dane 2, A1 |
| Quiz 5 | arkusze/Dodatki_swiateczne_23.xlsx | Zestawienie 1 … Zestawienie 4 |
| Quiz 6 | brak | – |
| Quiz 7 | brak | – |

Quizy bez arkusza: odpowiedź opieraj na PDF-ach z folderu materialy/.
Nazwy arkuszy (np. "Zestawienie") powtarzają się w różnych plikach. Zawsze najpierw ustal numer quizu.

## Odczyt danych
Źródło prawdy: pliki w arkusze/. Odczyt: Python + openpyxl (data_only=True dla wartości, bez data_only dla formuł).
Pomocniczo: dane-csv/<plik>__<arkusz>.csv. Kolumna "wiersz" = numer wiersza w Excelu, nagłówki = litery kolumn. Wartości formuł są wyliczone (cache Excela).
NIE czytaj automatycznego tekstu z .pplx/project-files/parse/ dla XLSX. Dla 04_Delegacje_quiz.xlsx ma 2,4 MB (arkusz A1 ma dane w kolumnie XFC) i jest ucinany.

Kontrola kompletności:
- 04_Delegacje_quiz: Dane 1 = 6 krajów (wiersze 2–7), Dane 2 = 131 osób (wiersze 2–132).
- Dodatki_swiateczne_23: Zestawienie 1–4 do wiersza 388.
- Podrozni_23: Podróżni_1–13 do wiersza 76.
- Ubezpiecznia-quiz_23: Ubezpieczenia 1 do wiersza 388; Zestawienie jest pusty.
