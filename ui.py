import os
import sys
import subprocess
import streamlit as st

BOT_INSTANCE = os.getenv("BOT_INSTANCE", "example")
LOG_FILE = "bot.log"

if "bot_process" not in st.session_state:
    st.session_state.bot_process = None

st.title("VictorGram Control Panel")

col1, col2 = st.columns(2)

with col1:
    if st.session_state.bot_process is None:
        if st.button("Start bot"):
            env = os.environ.copy()
            env["LOG_FILE"] = LOG_FILE
            st.session_state.bot_process = subprocess.Popen(
                [sys.executable, "app.py", BOT_INSTANCE], env=env
            )
    else:
        st.write("Bot is running")

with col2:
    if st.session_state.bot_process is not None:
        if st.button("Stop bot"):
            st.session_state.bot_process.terminate()
            st.session_state.bot_process.wait()
            st.session_state.bot_process = None
    else:
        st.write("Bot is stopped")

if st.button("Refresh logs"):
    pass

logs = ""
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = f.read()

st.text_area("Logs", logs, height=400)
