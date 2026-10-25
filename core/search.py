import re
from functools import lru_cache

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

@lru_cache(maxsize=1024)
def clean_moodle_prompt(text: str) -> str:
    text = re.sub(r"Information.*?Information text\s*", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"Question \d+.*?Question text\s*", "", text, flags=re.DOTALL | re.IGNORECASE)
    m = re.search(r"^(.*?)(?=(?:Question \d+Select one|Question \d+Answer|Select one:|Answera\.|[a-d]\.\s|[A-D]\.\s|\n[a-d]\.|\n[A-D]\.))", text, flags=re.DOTALL)
    if m:
        text = m.group(1)
    text = re.sub(r"\s+", " ", text).strip()
    return text

@lru_cache(maxsize=1024)
def normalize_exact_text(text: str) -> str:
    text = clean_moodle_prompt(text)
    text = text.lower().replace(",", ".")
    text = re.sub(r"(?:wynik|odpowiedź|formułę)[^.]*wpisz poniżej[:.]?", "", text)
    text = re.sub(r"\bw wierszu w wierszu\b", "w wierszu", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def to_alphanumeric(text: str) -> str:
    return re.sub(r"[^a-ząćęłńóśźż0-9]", "", text)

def has_conflict(q1: str, q2: str) -> bool:
    q1_low, q2_low = q1.lower(), q2.lower()
    for grp_a, grp_b in CONFLICT_PAIRS:
        in_a1 = any(w in q1_low for w in grp_a)
        in_b1 = any(w in q1_low for w in grp_b)
        in_a2 = any(w in q2_low for w in grp_a)
        in_b2 = any(w in q2_low for w in grp_b)
        if (in_a1 and in_b2 and not in_b1) or (in_b1 and in_a2 and not in_a1):
            return True
    return False

def extract_tokens(text: str):
    text = text.lower().replace(",", ".")
    words = set(re.findall(r"[a-ząćęłńóśźż0-9%]+", text))
    meaningful = words - STOPWORDS
    nums = set(re.findall(r"\d+(?:\.\d+)?%?", text))
    return meaningful, nums

class SearchIndex:
    def __init__(self, db_items: list):
        self.raw_db = db_items
        self.exact_map = {}
        self.alphanumeric_map = {}
        self.token_index = []
        self._build_index()

    def _build_index(self):
        for idx, item in enumerate(self.raw_db):
            q = item.get("pytanie", "")
            norm = normalize_exact_text(q)
            if norm:
                self.exact_map[norm] = item
                alpha = to_alphanumeric(norm)
                if alpha and alpha not in self.alphanumeric_map:
                    self.alphanumeric_map[alpha] = item
            
            klucze = " ".join(item.get("klucze", []))
            full_text = (q + " " + klucze).lower()
            words, nums = extract_tokens(full_text)
            self.token_index.append({
                "item": item,
                "full_text": full_text,
                "words": words,
                "nums": nums
            })

    def exact_match(self, query: str):
        q_norm = normalize_exact_text(query)
        if not q_norm:
            return None
        # O(1) hashmap lookup
        if q_norm in self.exact_map:
            return self.exact_map[q_norm]
        
        # Alphanumeric fallback
        q_alpha = to_alphanumeric(q_norm)
        if q_alpha in self.alphanumeric_map:
            return self.alphanumeric_map[q_alpha]
            
        for key, item in self.alphanumeric_map.items():
            if q_alpha in key or key in q_alpha:
                return item
        return None

    def smart_match(self, query: str, threshold: float = 0.80):
        q_words, q_nums = extract_tokens(query)
        q_clean = query.lower()
        best_item = None
        best_score = 0.0

        for entry in self.token_index:
            target_text = entry["full_text"]
            if has_conflict(query, target_text):
                continue

            t_words = entry["words"]
            t_nums = entry["nums"]

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

            if word_score < 0.4:
                continue

            # Szybki wskaźnik Jaccarda zamiast difflib SequenceMatcher
            union_len = len(q_words.union(t_words)) or 1
            jaccard = len(q_words.intersection(t_words)) / union_len
            total_score = 0.5 * num_score + 0.35 * word_score + 0.15 * jaccard

            if total_score > best_score:
                best_score = total_score
                best_item = entry["item"]

        if best_score >= threshold:
            return best_item, best_score
        return None, best_score
