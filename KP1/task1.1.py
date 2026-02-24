import pyttsx3
import speech_recognition as sr
import threading
import queue

# НАЛАШТУВАННЯ
config = {
    "mode": "mixed",
    "voice_index": -1,
    "rate": 160,
    "volume": 1.0,
}

text_queue = queue.Queue()


def tts_worker():
    while True:
        text = text_queue.get()
        if text == "__EXIT__":
            break

        if config["mode"] in ["oral", "mixed"]:
            try:
                temp_engine = pyttsx3.init('sapi5')
                voices = temp_engine.getProperty('voices')

                temp_engine.setProperty('voice', voices[config["voice_index"]].id)
                temp_engine.setProperty('rate', config["rate"])
                temp_engine.setProperty('volume', config["volume"])

                temp_engine.say(text)
                temp_engine.runAndWait()
                temp_engine.stop()
                del temp_engine
            except Exception as e:
                print(f"Помилка TTS: {e}")

        text_queue.task_done()


threading.Thread(target=tts_worker, daemon=True).start()


def process_commands(text):
    cmd = text.lower()

    # Зміна режиму
    if "режим текстовий" in cmd:
        config["mode"] = "text"
        return "Перейшов у текстовий режим."
    elif "режим голосовий" in cmd:
        config["mode"] = "oral"
        return "Перейшов у голосовий режим."
    elif "режим змішаний" in cmd:
        config["mode"] = "mixed"
        return "Увімкнув змішаний режим."

    # Зміна голосу
    elif "зміни голос" in cmd:
        return change_voice()

    # Зміна швидкості
    elif "швидше" in cmd:
        config["rate"] = min(config["rate"] + 40, 300)
        return "Збільшив швидкість."
    elif "повільніше" in cmd:
        config["rate"] = max(config["rate"] - 40, 80)
        return "Зменшив швидкість."

    # Зміна гучності
    elif "гучніше" in cmd:
        config["volume"] = min(config["volume"] + 0.2, 1.0)
        return "Додав гучності."
    elif "тихіше" in cmd:
        config["volume"] = max(config["volume"] - 0.2, 0.1)
        return "Зменшив гучність."

    return None


def change_voice():
    try:
        temp_engine = pyttsx3.init('sapi5')
        voices = temp_engine.getProperty('voices')
        num_voices = len(voices)

        if num_voices == 0:
            return "Голоси не знайдено."
        if config["voice_index"] == -1:
            config["voice_index"] = 0
        else:
            config["voice_index"] = (config["voice_index"] + 1) % num_voices

        selected_voice = voices[config["voice_index"]].name
        temp_engine.stop()
        del temp_engine
        return f"Голос змінено на: {selected_voice}"

    except Exception as e:
        return f"Помилка при зміні голосу: {e}"


# ОСНОВНИЙ ЦИКЛ
recognizer = sr.Recognizer()
print(
    "Echo-бот готовий до роботи. Доступні команди: 'режим текстовий/голосовий/змішаний', 'швидше', 'повільніше', 'зміни голос', 'гучніше/тихіше'")

try:
    while True:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("\n(Слухаю...)")

            try:
                audio = recognizer.listen(source, timeout=5)
                text = recognizer.recognize_google(audio, language="uk-UA")

                response = process_commands(text)

                if response:
                    print(f"Команда: {text} -> {response}")
                    text_queue.put(response)
                else:
                    if config["mode"] in ["text", "mixed"]:
                        print(f"Ви сказали: {text}")

                    text_queue.put(text)

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                print("Помилка API.")


except KeyboardInterrupt:
    print("\nВихід...")
    text_queue.put("__EXIT__")