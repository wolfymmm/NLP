import os
from transformers import pipeline

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

print("Завантаження моделі...")

qa_pipeline = pipeline(
    "question-answering",
    model="deepset/xlm-roberta-base-squad2"
)

print("Модель завантажена!")


try:
    with open("context.txt", "r", encoding="utf-8") as file:
        context = file.read()
except FileNotFoundError:
    print("Файл context.txt не знайдено!")
    exit()

print("\nКонтекст завантажено.")
print("Чат готовий! Питайте (введіть 'вихід' для завершення)\n")

# Чат
while True:
    question = input("Ваше питання: ")

    if question.lower() in ["вихід", "стоп", "quit"]:
        print("До побачення!")
        break

    result = qa_pipeline(
        question=question,
        context=context
    )

    if result["score"] < 0.2:
        print("Відповідь: У тексті немає інформації про це.")
    else:
        print("Відповідь:", result["answer"])