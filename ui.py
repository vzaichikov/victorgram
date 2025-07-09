import os
import sys
import glob
import subprocess
import time
import streamlit as st

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def list_instances():
    files = glob.glob(".env.*")
    names = []
    for f in files:
        name = f.split(".env.")[1]
        if name != "example":
            names.append(name)
    return sorted(names)


def read_new(filepath: str, pos: int):
    """Return new log data from pos and new position."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            f.seek(pos)
            data = f.read()
            return data, f.tell()
    except FileNotFoundError:
        return "", pos


if "process" not in st.session_state:
    st.session_state.process = None
if "logfile" not in st.session_state:
    st.session_state.logfile = None
if "log_pos" not in st.session_state:
    st.session_state.log_pos = 0
if "log_text" not in st.session_state:
    st.session_state.log_text = ""

st.title("VictorGram Manager")
instances = list_instances()
selected = st.selectbox("Instance", instances)

col1, col2 = st.columns(2)
if col1.button("Start"):
    if st.session_state.process is None:
        log_path = os.path.join(LOG_DIR, f"{selected}.log")
        log_file = open(log_path, "a", encoding="utf-8")
        proc = subprocess.Popen([sys.executable, "app.py", selected], stdout=log_file, stderr=log_file)
        st.session_state.process = proc
        st.session_state.logfile = log_path
        st.session_state.log_pos = 0
        st.session_state.log_text = ""

if col2.button("Stop"):
    if st.session_state.process is not None:
        st.session_state.process.terminate()
        st.session_state.process.wait()
        st.session_state.process = None

log_placeholder = st.empty()

if st.session_state.logfile:
    new_data, st.session_state.log_pos = read_new(
        st.session_state.logfile, st.session_state.log_pos
    )
    if new_data:
        st.session_state.log_text += new_data

    html = (
        "<div style='height:500px; overflow-y:auto; font-family:monospace; "
        "white-space: pre-wrap;'>" + st.session_state.log_text + "</div>"
    )
    log_placeholder.markdown(html, unsafe_allow_html=True)
    time.sleep(1)
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.rerun()
