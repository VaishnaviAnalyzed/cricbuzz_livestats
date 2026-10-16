"""Alias entry point (the brief names ``main.py``; the structure names ``app.py``).

Either works:  streamlit run app.py   |   streamlit run main.py
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
