import streamlit as st
import speech_recognition as sr
import tempfile
import os
import win32com.client
import pythoncom
import base64
import threading

sapi_lock = threading.Lock()

st.set_page_config(page_title="Echo-чат", page_icon="Logo Wechat.svg", layout="centered")


# Ініціалізація стану
if "messages" not in st.session_state:
    st.session_state.messages = []

if "config" not in st.session_state:
    pythoncom.CoInitialize()
    try:
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        voices = speaker.GetVoices()
        voice_list = [voices.Item(i).GetDescription() for i in range(voices.Count)]
    except Exception:
        voice_list = []
    finally:
        pythoncom.CoUninitialize()

    st.session_state.config = {
        "rate": 0,
        "volume": 100,
        "voice_index": 0,
        "voices": voice_list
    }

if "last_processed_key" not in st.session_state:
    st.session_state.last_processed_key = None


# Функції обробки
def synthesize_to_base64(text):
    with sapi_lock:
        pythoncom.CoInitialize()
        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            cfg = st.session_state.config

            voices = speaker.GetVoices()
            if voices.Count > 0:
                idx = min(cfg["voice_index"], voices.Count - 1)
                speaker.Voice = voices.Item(idx)

            speaker.Rate = cfg["rate"]
            speaker.Volume = cfg["volume"]

            fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)

            file_stream = win32com.client.Dispatch("SAPI.SpFileStream")
            file_stream.Open(tmp_path, 3)
            speaker.AudioOutputStream = file_stream
            speaker.Speak(text)
            file_stream.Close()

            with open(tmp_path, "rb") as f:
                data = f.read()

            os.remove(tmp_path)
            return base64.b64encode(data).decode()
        except Exception as e:
            st.error(f"Помилка синтезу: {e}")
            return None
        finally:
            pythoncom.CoUninitialize()


def recognize_audio(audio_bytes):
    recognizer = sr.Recognizer()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        with sr.AudioFile(tmp_path) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language="uk-UA")
    except Exception:
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# Інтерфейс
st.title("Echo-чат")

with st.sidebar:
    st.header("⚙️ Налаштування")
    mode = st.radio(
        "Режим відповідей",
        options=["Тільки текстові", "Тільки голосові", "Змішані"],
        index=2,
        key="mode_radio"
    )

    st.session_state.config["rate"] = st.slider("Швидкість", -10, 10, st.session_state.config["rate"])
    st.session_state.config["volume"] = st.slider("Гучність", 0, 100, st.session_state.config["volume"])

    if st.session_state.config["voices"]:
        st.session_state.config["voice_index"] = st.selectbox(
            "Голос",
            range(len(st.session_state.config["voices"])),
            format_func=lambda i: st.session_state.config["voices"][i],
            index=st.session_state.config["voice_index"]
        )

    if st.button("Очистити чат"):
        st.session_state.messages = []
        st.session_state.last_processed_key = None
        st.rerun()

# Відображення повідомлень
chat_placeholder = st.container()

with chat_placeholder:
    for i, msg in enumerate(st.session_state.messages):
        is_last = (i == len(st.session_state.messages) - 1)
        with st.chat_message(msg["role"]):
            if msg["role"] == "user" or mode != "Тільки голосові":
                st.write(msg["content"])

            if msg["role"] == "assistant" and msg.get("audio_b64") and mode != "Тільки текстові":
                if is_last:
                    st.markdown(f"""
                        <div class="audio-wave">
                            <div class="bar" style="animation-delay: 0.0s"></div>
                            <div class="bar" style="animation-delay: 0.2s"></div>
                            <div class="bar" style="animation-delay: 0.4s"></div>
                            <span style="font-size: 0.8em; color: #00ccff; margin-left: 10px;">Відтворюється...</span>
                        </div>
                        <audio autoplay src="data:audio/wav;base64,{msg['audio_b64']}"></audio>
                    """, unsafe_allow_html=True)
                else:
                    st.audio(base64.b64decode(msg['audio_b64']), format="audio/wav")

# Ввід даних
audio_input = st.audio_input("Запишіть повідомлення", key="voice_input")

# Логіка для аудіо-вводу
if audio_input:
    current_key = f"{audio_input.name}_{audio_input.size}"

    if st.session_state.last_processed_key != current_key:
        st.session_state.last_processed_key = current_key

        with st.spinner("Розпізнаю голос..."):
            recognized_text = recognize_audio(audio_input.getvalue())

        if recognized_text:
            st.session_state.messages.append({"role": "user", "content": recognized_text})

            audio_b64 = None
            if mode != "Тільки текстові":
                with st.spinner("Синтезую відповідь..."):
                    audio_b64 = synthesize_to_base64(recognized_text)

            st.session_state.messages.append({
                "role": "assistant",
                "content": recognized_text,
                "audio_b64": audio_b64
            })
            st.rerun()

# Логіка для текстового вводу
if prompt := st.chat_input("Або напишіть повідомлення тут..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    audio_b64 = None
    if mode != "Тільки текстові":
        audio_b64 = synthesize_to_base64(prompt)

    st.session_state.messages.append({
        "role": "assistant",
        "content": prompt,
        "audio_b64": audio_b64
    })
    st.rerun()