import os
import streamlit as st
import pandas as pd
from datetime import datetime
from engine.option_chain_engine import get_expiries, get_option_chain, parse_option_chain, final_signal

st.set_page_config(page_title="Trade Burner Terminal", page_icon="🔥", layout="wide")

st.markdown("""<style>
.block-container{padding-top:1.2rem;max-width:1500px}
.tb-card{padding:18px;border:1px solid #2b2f36;border-radius:14px;background:#111318;margin-bottom:12px}
.tb-title{font-size:30px;font-weight:800}.muted{color:#8d95a1}.signal{font-size:22px;font-weight:800}
</style>""", unsafe_allow_html=True)

st.markdown('<div class="tb-title">🔥 TRADE BURNER <span class="muted">TERMINAL V1</span></div>', unsafe_allow_html=True)
st.caption("Complex analysis in the backend. Simple decision on the screen.")

with st.sidebar:
    st.header("Terminal")
    mode=st.radio("Mode", ["Dashboard","Index Options","Stock Scanner","Strategies","Risk Manager","Journal"])
    st.divider()
    auto=st.checkbox("Auto refresh", value=False)
    interval=st.number_input("Refresh seconds", min_value=10, max_value=300, value=30, step=5)
    if st.button("Refresh now", use_container_width=True): st.rerun()

if mode in ["Dashboard","Index Options"]:
    st.subheader("📊 Index Options")
    expiries=get_expiries()
    if not expiries:
        st.error("Expiry list nahi mili. Check DHAN_ACCESS_TOKEN.")
        st.stop()
    expiry=st.selectbox("Expiry", expiries, index=0)
    if st.button("Analyze Option Chain", type="primary") or mode=="Dashboard":
        response=get_option_chain(expiry)
        if response is None:
            st.error("Option Chain data nahi mila.")
            st.stop()
        data=parse_option_chain(response, expiry)
        if data is None:
            st.error("Option Chain parse failed.")
            st.stop()
        result=final_signal(data)
        bias=result["Option_Bias"]
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Spot", f'{result["Spot"]:.2f}')
        c2.metric("ATM", f'{result["ATM"]:.0f}')
        c3.metric("PCR", f'{result["PCR"]:.2f}')
        c4.metric("Bias", bias)
        st.divider()
        if result["Suggested_Option"]:
            st.markdown('<div class="tb-card">',unsafe_allow_html=True)
            a,b,c,d,e=st.columns(5)
            a.metric("🔥 Setup", result["Suggested_Option"])
            b.metric("Entry", f'{result["Entry"]:.2f}')
            c.metric("SL", f'{result["Stop_Loss"]:.2f}')
            d.metric("Target 1", f'{result["Target_1"]:.2f}')
            e.metric("Target 2", f'{result["Target_2"]:.2f}')
            st.success("⏳ WAIT FOR ENTRY — Do not enter simply at CMP.")
            st.markdown('</div>',unsafe_allow_html=True)
        else:
            st.warning("🛑 NO TRADE — Option chain does not meet the current signal rules.")
        st.subheader("📋 Option Chain")
        st.dataframe(data["selected"], use_container_width=True, hide_index=True)
        with st.expander("Why this setup?"):
            st.write(f'Bias: {bias}')
            st.write(f'Put support: {result["Put_Support"]:.0f}')
            st.write(f'Call resistance: {result["Call_Resistance"]:.0f}')
            st.write(f'Put Change OI max: {result["Put_ChangeOI_Support"]:.0f}')
            st.write(f'Call Change OI max: {result["Call_ChangeOI_Resistance"]:.0f}')
            st.write(f'Bullish score: {result["Bullish_Score"]}')
            st.write(f'Bearish score: {result["Bearish_Score"]}')
else:
    st.info(f"{mode} module — V1 foundation ready. We will plug this module into the terminal next.")

st.caption(f"Last UI update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
if auto:
    st.markdown(f'<meta http-equiv="refresh" content="{int(interval)}">', unsafe_allow_html=True)
