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


def tail(filepath, lines=40):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = f.readlines()
        return "".join(data[-lines:])
    except FileNotFoundError:
        return ""


if "process" not in st.session_state:
    st.session_state.process = None
if "logfile" not in st.session_state:
    st.session_state.logfile = None

st.title("VictorGram Manager")
instances = list_instances()
selected = st.selectbox("Instance", instances)

col1, col2 = st.columns(2)
if col1.button("Start"):
    if st.session_state.process is None:
        log_path = os.path.join(LOG_DIR, f"{selected}.log")
        log_file = open(log_path, "a")
        proc = subprocess.Popen([sys.executable, "app.py", selected], stdout=log_file, stderr=log_file)
        st.session_state.process = proc
        st.session_state.logfile = log_path

if col2.button("Stop"):
    if st.session_state.process is not None:
        st.session_state.process.terminate()
        st.session_state.process.wait()
        st.session_state.process = None

log_placeholder = st.empty()

if st.session_state.logfile:
    log_placeholder.text(tail(st.session_state.logfile, 40))
    time.sleep(1)
    st.experimental_rerun()
