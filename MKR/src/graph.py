import textacy
import spacy
from pyvis.network import Network
import os
import re

nlp = spacy.load("uk_core_news_lg")

def get_sentiment_color(text):
    """Визначає колір зв'язку: зелений - за, червоний - проти, сірий - нейтрально"""
    pos_words = {"підтримати", "схвалити", "важливо", "необхідно", "позитивно", "ефективно", "успіх", "за"}
    neg_words = {"проти", "ганьба", "криза", "неприпустимо", "відхилити", "провал", "помилка", "вороги"}
    
    text_lower = text.lower()
    pos_score = sum(1 for w in pos_words if w in text_lower)
    neg_score = sum(1 for w in neg_words if w in text_lower)
    
    if pos_score > neg_score: return "#2ecc71"  
    if neg_score > pos_score: return "#e74c3c"  
    return "#95a5a6" 

def extract_decision_titles(text):
    """Витягує назви рішень та номери (як у файлі аналізу)"""
    decisions = []
    patterns = [
        r"(?:проект\s+)?(?:закону|постанови|рішення)\s+про\s+[^.\n]+",
        r"питання\s+(?:про|щодо)\s+[^.\n]+",
        r"звільнення\s+[^.\n]+",
        r"призначення\s+[^.\n]+"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            title = m.group(0).strip()
            if len(title) > 80:  
                title = title[:80] + "..."
            decisions.append(title)
            
    bill_no = re.findall(r"(?:№|номер)\s*(\d+[-\d]*)", text)
    for b in bill_no:
        decisions.append(f"Законопроект № {b}")
        
    return list(set(decisions))

def build_parliament_graph(corpus_path):
    if not os.path.exists(corpus_path):
        print(f"Помилка: Корпус {corpus_path} не знайдено!")
        return

    print(f"Завантаження корпусу для побудови графа...")
    corpus = textacy.Corpus.load(nlp, corpus_path)
    
    net = Network(height="850px", width="100%", bgcolor="#ffffff", font_color="black")
    net.barnes_hut(gravity=-10000, central_gravity=0.3, spring_length=200)


    nodes_added = set()
    edges_added = set()

    for doc in corpus:
        meta = doc._.meta
        speaker = meta.get('speaker')
        faction = meta.get('faction', 'Позафракційні')
        
        if not speaker:
            continue

        decisions = extract_decision_titles(doc.text)
        
        if decisions:
            if speaker not in nodes_added:
                net.add_node(speaker, label=speaker, title=f"Фракція: {faction}", 
                             color="#3498db", size=60, shape="dot")
                nodes_added.add(speaker)
                
            
            sentiment_color = get_sentiment_color(doc.text)

            for title in decisions:
                if title not in nodes_added:
                    net.add_node(title, label=title, title="Предмет обговорення", 
                                 color="#f1c40f", size=60, shape="diamond")
                    nodes_added.add(title)
                
                edge_key = tuple(sorted((speaker, title)))
                if edge_key not in edges_added:
                    net.add_edge(speaker, title, color=sentiment_color, width=6)
                    edges_added.add(edge_key)

    output_file = "output/parliament_graph.html"
    os.makedirs("output", exist_ok=True)
    
    net.save_graph(output_file)
    print(f"Граф успішно створено: {output_file}")
    print(f"Усього вузлів: {len(nodes_added)}, зв'язків: {len(edges_added)}")

if __name__ == "__main__":
    build_parliament_graph("output/parliament_v2.bin.gz")