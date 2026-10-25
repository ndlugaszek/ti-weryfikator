import os
import re
import csv
from typing import Tuple, Optional, Dict, List

def calculate_from_csv(query: str, csv_cache: Dict[str, List[List[str]]]) -> Tuple[Optional[str], Optional[str]]:
    q_low = query.lower().replace(",", ".")
    
    # QUIZ 3: UBEZPIECZENIA 1
    if any(k in q_low for k in ["ubezpiecz", "do zapłaty", "car assistance", "samochód zastępczy", "samochodu zastępczego", "autoalarm", "immobilizer", "blokad"]):
        rows = csv_cache.get("Ubezpiecznia-quiz_23__Ubezpieczenia_1.csv")
        if rows:
            data_rows = rows[4:]

            # Zliczanie wyposażenia dodatkowego
            if "wyposażeni" in q_low and "dodatkow" in q_low and not any(k in q_low for k in ["vip", "mniej niż 15", "samochod", "bagaż"]):
                if "nie zadeklarowało" in q_low:
                    cnt = sum(1 for r in data_rows if r[8].strip() == "")
                    return str(cnt), f"Liczba klientów, którzy nie zadeklarowali wyposażenia = {cnt}"
                if "nie skorzysta" in q_low or "nie będą korzystać" in q_low:
                    cnt = sum(1 for r in data_rows if r[8].strip().lower() == "nie")
                    return str(cnt), f"Liczba klientów, którzy nie skorzystają z wyposażenia = {cnt}"
                if "skorzysta" in q_low or "korzysta" in q_low:
                    cnt = sum(1 for r in data_rows if r[8].strip().lower() == "tak")
                    return str(cnt), f"Liczba klientów korzystających z wyposażenia = {cnt}"

            if "standard" in q_low and ("samochod" in q_low or "samochód" in q_low or "dni" in q_low):
                if "więcej niż 5" in q_low or "> 5" in q_low or ">5" in q_low or "15 dni" in q_low:
                    filtered = [r for r in data_rows if r[7].strip().lower() == "standard" and r[9].strip() == "15"]
                    if "kwot" in q_low and "ubezpiecz" in q_low:
                        avg = sum(float(r[3]) for r in filtered) / len(filtered)
                        return f"{avg:.2f}", f"Średnia kwota ubezpieczenia (Standard + Samochód > 5 dni / 15 dni; {len(filtered)} klientów) = {avg:.2f}"
                    if "do zapłaty" in q_low:
                        avg = sum(float(r[10]) for r in filtered) / len(filtered)
                        return f"{avg:.2f}", f"Średnia kwota do zapłaty (Standard + Samochód > 5 dni / 15 dni; {len(filtered)} klientów) = {avg:.2f}"
                elif "co najmniej 5" in q_low or ">= 5" in q_low or ">=5" in q_low:
                    filtered = [r for r in data_rows if r[7].strip().lower() == "standard" and r[9].strip() in ["5", "15"]]
                    if "do zapłaty" in q_low:
                        avg = sum(float(r[10]) for r in filtered) / len(filtered)
                        return f"{round(avg, 1)}", f"Średnia kwota do zapłaty (Standard + Samochód >= 5 dni; {len(filtered)} klientów) = {round(avg, 1)}"
                    if "kwot" in q_low and "ubezpiecz" in q_low:
                        avg = sum(float(r[3]) for r in filtered) / len(filtered)
                        return f"{avg:.2f}", f"Średnia kwota ubezpieczenia (Standard + Samochód >= 5 dni; {len(filtered)} klientów) = {avg:.2f}"

            if "mniej niż 15" in q_low or ("nie będą korzystać" in q_low and "samochod" in q_low):
                filtered = [r for r in data_rows if r[8].strip().lower() == "nie" and r[9].strip() in ["2", "5"]]
                if "do zapłaty" in q_low:
                    s = sum(float(r[10]) for r in filtered)
                    return str(int(s)), f"Łączna kwota do zapłaty dla wyposażenie='nie' i samochód < 15 dni ({len(filtered)} klientów) = {int(s)}"
                if "ubezpiecz" in q_low:
                    s = sum(float(r[3]) for r in filtered)
                    return str(int(s)), f"Łączna kwota ubezpieczenia dla wyposażenie='nie' i samochód < 15 dni ({len(filtered)} klientów) = {int(s)}"
                s = sum(float(r[10]) for r in filtered) if "zapłat" in q_low else sum(float(r[3]) for r in filtered)
                return str(int(s)), f"Kalkulacja dla wyposażenie='nie' i samochód < 15 dni ({len(filtered)} klientów) = {int(s)}"

            if "autoalarm" in q_low and "blokad" in q_low:
                filtered = [r for r in data_rows if r[4].strip() == "+" and r[6].strip() == "+"]
                if "do zapłaty" in q_low:
                    s = sum(float(r[10]) for r in filtered)
                    return str(int(s)), f"Łączna kwota do zapłaty (Autoalarm + Blokada; {len(filtered)} klientów) = {int(s)}"
                if "kwota ubezpieczenia" in q_low or "kwotę ubezpieczenia" in q_low:
                    s = sum(float(r[3]) for r in filtered)
                    return str(int(s)), f"Łączna kwota ubezpieczenia (Autoalarm + Blokada; {len(filtered)} klientów) = {int(s)}"

            if "vip" in q_low and ("dodatkow" in q_low or "wyposażeni" in q_low):
                filtered = [r for r in data_rows if r[7].strip().lower() == "vip" and r[8].strip() == "tak"]
                if "do zapłaty" in q_low and "średni" in q_low:
                    avg = sum(float(r[10]) for r in filtered) / len(filtered)
                    return f"{round(avg, 1)}", f"Średnia kwota do zapłaty (VIP + wyposażenie 'tak') = {round(avg, 1)}"
                if "ubezpiecz" in q_low and "średni" in q_low:
                    avg = sum(float(r[3]) for r in filtered) / len(filtered)
                    return f"{round(avg, 1)}", f"Średnia kwota ubezpieczenia (VIP + wyposażenie 'tak') = {round(avg, 1)}"

            if ("samochod" in q_low or "samochód" in q_low) and not any(k in q_low for k in ["standard", "vip", "bagaż", "wyposażeni", "kwot", "do zapłaty", "średni"]):
                if "co najmniej 5" in q_low or ">= 5" in q_low or ">=5" in q_low:
                    cnt = sum(1 for r in data_rows if r[9].strip() in ["5", "15"])
                    return str(cnt), f"Liczba klientów z samochodem zastępczym >= 5 dni = {cnt}"
                if "nie więcej niż 5" in q_low or "<= 5" in q_low or "<=5" in q_low:
                    cnt = sum(1 for r in data_rows if r[9].strip() in ["2", "5"])
                    return str(cnt), f"Liczba klientów z samochodem zastępczym <= 5 dni = {cnt}"
                if "dokładnie 2" in q_low or "przez 2 dni" in q_low:
                    cnt = sum(1 for r in data_rows if r[9].strip() == "2")
                    return str(cnt), f"Liczba klientów z samochodem zastępczym na 2 dni = {cnt}"
                if "dokładnie 5" in q_low or "przez 5 dni" in q_low:
                    cnt = sum(1 for r in data_rows if r[9].strip() == "5")
                    return str(cnt), f"Liczba klientów z samochodem zastępczym na 5 dni = {cnt}"
                if "15 dni" in q_low or "więcej niż 5" in q_low:
                    cnt = sum(1 for r in data_rows if r[9].strip() == "15")
                    return str(cnt), f"Liczba klientów z samochodem zastępczym na 15 dni = {cnt}"

            if "nie więcej niż 300" in q_low or "<= 300" in q_low or "<=300" in q_low:
                cnt = sum(1 for r in data_rows if float(r[10]) <= 300)
                return str(cnt), f"Liczba klientów z kwotą do zapłaty <= 300 zł = {cnt}"

            m_gte = re.search(r"co najmniej\s+(\d+)", q_low)
            if m_gte and ("kwot" in q_low or "ubezpiecz" in q_low):
                limit = float(m_gte.group(1))
                cnt = sum(1 for r in data_rows if float(r[3]) >= limit)
                return str(cnt), f"Liczba klientów z kwotą ubezpieczenia >= {int(limit)} = {cnt}"

            if "do zapłaty" in q_low:
                vals = [float(r[10]) for r in data_rows]
                if "najwyższ" in q_low or "maksymaln" in q_low:
                    return str(int(max(vals))), f"MAX(J7:J388) na kolumnie Do zapłaty = {int(max(vals))}"
                if "najniższ" in q_low or "minimaln" in q_low:
                    return str(int(min(vals))), f"MIN(J7:J388) na kolumnie Do zapłaty = {int(min(vals))}"
                if "łączn" in q_low or "suma" in q_low:
                    return str(int(sum(vals))), f"SUMA(J7:J388) na kolumnie Do zapłaty = {int(sum(vals))}"
                if "średni" in q_low and "wszystkich" in q_low:
                    return f"{sum(vals)/len(vals):.2f}", f"ŚREDNIA(J7:J388) na kolumnie Do zapłaty = {sum(vals)/len(vals):.2f}"

            if "kwota ubezpieczenia" in q_low or "kwotę ubezpieczenia" in q_low:
                vals = [float(r[3]) for r in data_rows]
                if "najwyższ" in q_low or "maksymaln" in q_low:
                    return str(int(max(vals))), f"MAX(C7:C388) na kolumnie Kwota ubezpieczenia = {int(max(vals))}"
                if "najniższ" in q_low or "minimaln" in q_low:
                    return str(int(min(vals))), f"MIN(C7:C388) na kolumnie Kwota ubezpieczenia = {int(min(vals))}"
                if "łączn" in q_low or "suma" in q_low:
                    return str(int(sum(vals))), f"SUMA(C7:C388) na kolumnie Kwota ubezpieczenia = {int(sum(vals))}"
                if "średni" in q_low and "wszystkich" in q_low:
                    return f"{sum(vals)/len(vals):.2f}", f"ŚREDNIA(C7:C388) na kolumnie Kwota ubezpieczenia = {sum(vals)/len(vals):.2f}"

    # QUIZ 4: WYKRESY KOŁOWE (DANE 1)
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
