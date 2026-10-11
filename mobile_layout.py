"""Responsive styles shared by the existing Streamlit trading page."""

MOBILE_CSS = """
<style>
.st-key-price_chart .modebar {max-width:100%; overflow-x:auto;}
.st-key-price_chart .modebar-group {float:none; display:inline-block;}
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
[data-testid="stRadio"] label p {color:#c9d7e2 !important;}
@media (max-width: 767px) {
  .st-key-market_source_detail, .st-key-main_home {display:none;}
  .block-container {padding:.5rem .5rem calc(1rem + env(safe-area-inset-bottom)) !important;}
  [data-testid="stElementContainer"]:has(.brand) {display:none;}
  [data-testid="stVerticalBlock"] {gap:.35rem;}
  [data-testid="stVerticalBlockBorderWrapper"] > div {padding:.45rem !important;}
  .st-key-price_chart h3 {font-size:17px;padding:.2rem 0;}
  .st-key-training_controls [data-testid="stHorizontalBlock"] {flex-wrap:nowrap !important;}
  .st-key-training_controls [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {width:auto !important;flex:1 1 0 !important;}
  .sub {display:block;margin:0;font-size:12px;}
  .stButton button {min-height:44px;touch-action:manipulation;}
  input, textarea, [role="combobox"] {font-size:16px !important;}
  [data-testid="stColumn"] {min-width:0 !important;}
  :is(.st-key-training_controls, .st-key-training_controls > [data-testid="stVerticalBlock"]) > [data-testid="stHorizontalBlock"] {
    flex-wrap:nowrap !important;gap:.4rem !important;
  }
  :is(.st-key-training_controls, .st-key-training_controls > [data-testid="stVerticalBlock"]) > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {
    width:35% !important;flex:1 1 35% !important;
  }
  :is(.st-key-training_controls, .st-key-training_controls > [data-testid="stVerticalBlock"]) > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
    width:65% !important;flex:1 1 65% !important;
  }
  .st-key-training_controls [data-testid="stHorizontalBlock"] {gap:.35rem;}
  .st-key-training_controls h3 {font-size:1.05rem;}
  .st-key-training_controls button {font-size:13px;padding:.3rem;}
  .st-key-training_controls button [data-testid="stKeyboardShortcut"] {display:none;}
  .st-key-training_controls [data-testid="stRadio"] label {min-height:44px;}
  .st-key-price_chart .modebar {top:auto !important;bottom:36px !important;}
  .st-key-training_controls [data-testid="stCaptionContainer"] {font-size:11px;}
  .st-key-price_chart [data-testid="stHorizontalBlock"] {flex-wrap:nowrap !important;}
  .st-key-price_chart [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {width:auto !important;flex:1 1 0 !important;}
}
</style>
"""
