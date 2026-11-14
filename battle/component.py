"""Register the browser terminal under a stable ASCII package module."""
from pathlib import Path
import streamlit.components.v1 as components

terminal = components.declare_component(
    'onion_battle_terminal', path=str(Path(__file__).resolve().parent / 'frontend')
)
