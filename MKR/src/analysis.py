import textacy
from textacy import extract
import spacy
from collections import defaultdict
import os
import re

nlp = spacy.load("uk_core_news_lg")

def get_sentiment(text):
    """Визначення тональності виступу"""
    pos_words = {"підтримати", "схвалити", "важливо", "необхідно", "позитивно", "ефективно", "успіх", "за"}
    neg_words = {"проти", "ганьба", "криза", "неприпустимо", "відхилити", "провал", "помилка", "вороги"}
    
    text_lower = text.lower()
    pos_score = sum(1 for w in pos_words if w in text_lower)
    neg_score = sum(1 for w in neg_words if w in text_lower)
    
    if pos_score > neg_score: return "Позитивне"
    if neg_score > pos_score: return "Негативне"
    return "Нейтральне"

def extract_decision_titles(doc):
    """Витягує назви рішень на основі ключових слів"""
    decisions = []
    patterns = [
        r"(?:проект\s+)?(?:закону|постанови|рішення)\s+про\s+[^.\n]+",
        r"питання\s+(?:про|щодо)\s+[^.\n]+",
        r"звільнення\s+[^.\n]+",
        r"призначення\s+[^.\n]+"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, doc.text, re.IGNORECASE)
        for m in matches:
            title = m.group(0).strip()
            if len(title) > 100:
                title = title[:100] + "..."
            decisions.append(title)
            
    bill_no = re.findall(r"(?:№|номер)\s*(\d+[-\d]*)", doc.text)
    for b in bill_no:
        decisions.append(f"Законопроект № {b}")
        
    return list(set(decisions))

def analyze_global_decisions(corpus_path):
    if not os.path.exists(corpus_path):
        print("Файл корпусу не знайдено!")
        return

    corpus = textacy.Corpus.load(nlp, corpus_path)
    
    decisions_db = defaultdict(lambda: {"votes": "Обговорення", "speakers": []})
    vote_re = re.compile(r"За-(\d+)")
    
    # Лічильники
    total_speakers = set()
    total_decisions_count = 0
    accepted_count = 0
    rejected_count = 0
    discussed_only_count = 0

    print("АНАЛІЗ КОРПУСУ...")

    for doc in corpus:
        meta = doc._.meta
        text = doc.text
        
        if meta.get('speaker'):
            total_speakers.add(meta['speaker'])
        
        titles = extract_decision_titles(doc)
        sentiment = get_sentiment(text)
        vote_match = vote_re.search(text)
        
        for title in titles:
            if vote_match:
                decisions_db[title]["votes"] = vote_match.group(1)
            
            decisions_db[title]["speakers"].append({
                "name": meta['speaker'],
                "faction": meta.get('faction', 'Позафракційні'),
                "sentiment": sentiment
            })

    print("\n" + "="*100)
    print(f"{'НАЗВА РІШЕННЯ / ПРЕДМЕТ ОБГОВОРЕННЯ':<60} | {'ГОЛОСИ':<8} | {'СТАТУС'}")
    print("="*100)

    for title, data in decisions_db.items():
        total_decisions_count += 1
        votes = data["votes"]
        
        if votes.isdigit():
            v_int = int(votes)
            if v_int >= 226:
                status = "ПРИЙНЯТО ✅"
                accepted_count += 1
            else:
                status = "НЕ ПРИЙНЯТО ❌"
                rejected_count += 1
        else:
            status = "ОБГОВОРЕННЯ 💬"
            discussed_only_count += 1
            
        print(f"{title[:58]:<60} | {votes:<8} | {status}")
        
        if data["speakers"]:
            unique_speakers = {s['name']: s for s in data["speakers"]}.values()
            for s in unique_speakers:
                print(f"   └─ {s['sentiment']} {s['name']} ({s['faction']})")
        print("-" * 100)

    print("\nЗАГАЛЬНА СТАТИСТИКА ЗАСІДАННЯ:")
    print(f"Усього унікальних спікерів у залі: {len(total_speakers)}")
    print(f"Усього виявлено рішень/проєктів: {total_decisions_count}")
    print(f"Прийнято (226+ голосів): {accepted_count}")
    print(f"Відхилено (менше 226): {rejected_count}")
    print(f"Тільки обговорювались (без голосування): {discussed_only_count}")
    print("="*100)

if __name__ == "__main__":
    analyze_global_decisions("output/parliament_v2.bin.gz")