import spacy
from spacy.matcher import Matcher
import textacy
import os
from pathlib import Path
import re
from config import party_mapping 

nlp = spacy.load("uk_core_news_lg")
matcher = Matcher(nlp.vocab)

pattern_role = [
    {"SHAPE": "dd:dd:dd"}, 
    {"IS_SPACE": True, "OP": "*"}, 
    {"TEXT": {"IN": ["ГОЛОВУЮЧИЙ", "ГОЛОВУЮЧА", "ГОЛОВА", "Головуючий", "Головуюча", "Голова"]}},
    {"TEXT": {"IN": [".", ":"]}, "OP": "?"}
]

pattern_surname = [
    {"SHAPE": "dd:dd:dd"},
    {"IS_SPACE": True, "OP": "*"},
    {"IS_UPPER": True, "LENGTH": {">=": 2}}, 
    {"TEXT": {"REGEX": r"^[А-ЯІЇЄ]\.$"}}, 
    {"TEXT": {"REGEX": r"^[А-ЯІЇЄ]\.$"}, "OP": "?"}
]

matcher.add("SPEAKER_HEADER", [pattern_role, pattern_surname])

def clean_speaker_name(name_text):
    return re.sub(r'[:.]$', '', name_text).strip()

def create_corpus_with_matcher(file_path, speech_date):
    if not os.path.exists(file_path):
        print(f"Файл {file_path} не знайдено.")
        return None

    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    doc = nlp.make_doc(text)
    matches = matcher(doc)
    records = []
    
    for i, (match_id, start, end) in enumerate(matches):
        # Визначаємо межі тексту виступу
        next_start = matches[i+1][1] if i+1 < len(matches) else len(doc)
        
        speech_time = doc[start].text
        # Токен 0 - час, токени від 1 до кінця матчу - ім'я
        speaker_raw = doc[start + 1 : end].text
        speaker_name = clean_speaker_name(speaker_raw)
        speech_text = doc[end : next_start].text.strip()

        if speech_text:
            speaker_key = speaker_name.upper()
            if speaker_key not in party_mapping:
                print(f"Спікер '{speaker_name}' відсутній у словнику, позначено як Позафракційний")
            
            faction = party_mapping.get(speaker_key, "Позафракційні")
            
            record = (
                speech_text, 
                {
                    "speaker": speaker_name,
                    "date_time": f"{speech_date}T{speech_time}",
                    "source": os.path.basename(file_path),
                    "faction": faction
                }
            )
            records.append(record)

    if records:
        return textacy.Corpus(nlp, data=records)
    return None

file_name = "data/2020-03-04__POZACERHOVE_ZASIDANNJa.txt"
speech_date = "2020-03-04"

corpus = create_corpus_with_matcher(file_name, speech_date)

if corpus:
    print(f"Оброблено документів: {len(corpus)}")
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "parliament_v2.bin.gz"
    corpus.save(str(output_file))
    print(f"✅ Корпус успішно збережено у: {output_file}")