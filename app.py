# app.py - FINAL FIXED VERSION (All answer_question calls updated)
import streamlit as st
import pandas as pd
from utils import process_cvs_final, answer_question, get_candidates_df

st.set_page_config(page_title="⚡ HR AI", page_icon="🤖", layout="wide")

# CSS
st.markdown("""
<style>
    .stDataFrame { font-size: 14px; border-radius: 8px; }
    .log { font-family: monospace; font-size: 12px; background: #f8f9fa; padding: 8px; border-radius: 4px; }
    .answer-box { background: #f0f7ff; padding: 15px; border-radius: 8px; border-left: 4px solid #2196F3; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ HR AI Assistant")

# Session State
for key in ["vectorstore", "candidates", "messages", "log", "debug_mode", "trigger_question", "processing"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "vectorstore" else ([] if key not in ["debug_mode", "processing", "trigger_question"] else False)

# Sidebar
with st.sidebar:
    st.header("📤 Upload CVs")
    files = st.file_uploader("PDF Files", type="pdf", accept_multiple_files=True)
    st.session_state.debug_mode = st.checkbox("🐛 Debug Mode", value=False)
    
    if st.button("🔄 Process CVs", type="primary", use_container_width=True):
        if files:
            with st.spinner("Processing..."):
                vs, candidates, log = process_cvs_final(files, st.session_state.debug_mode)
                st.session_state.vectorstore = vs
                st.session_state.candidates = candidates
                st.session_state.log = log
                st.session_state.messages = []
                st.success(f"✅ {len(candidates)} CVs ready!")
        else:
            st.warning("Select files first")
    
    st.divider()
    st.subheader("🔍 Pipeline Log")
    if st.session_state.log:
        for entry in st.session_state.log:
            st.markdown(f"<div class='log'>{entry}</div>", unsafe_allow_html=True)
    
    if st.session_state.candidates:
        st.divider()
        st.metric("📊 Candidates", len(st.session_state.candidates))

# ==========================================
# 🎯 TABS: Clean Separation
# ==========================================
tab_chat, tab_data = st.tabs(["💬 Ask Questions", "📋 Candidates Data"])

# ==========================================
# TAB 1: CHAT (Text Answers Only)
# ==========================================
with tab_chat:
    st.subheader("⚡ Quick Questions")
    qs = [
        "Who has Python experience?",
        "Show candidates with SQL skills", 
        "Who is suitable for AI Engineer role?",
        "List all names and titles"
    ]
    
    cols = st.columns(4)
    for i, (col, q) in enumerate(zip(cols, qs)):
        if col.button(q, key=f"q_{i}", use_container_width=True):
            st.session_state.trigger_question = q
            st.session_state.processing = True
    
    # Process triggered question (ONCE)
    if st.session_state.get("processing") and st.session_state.get("trigger_question"):
        question = st.session_state.trigger_question
        st.session_state.messages.append({"role": "user", "content": question})
        
        with st.chat_message("user"):
            st.markdown(question)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # ✅ FIXED: Pass candidates to answer_question
                if any(kw in question.lower() for kw in ["table", "csv", "export", "spreadsheet", "excel"]):
                    df = get_candidates_df(st.session_state.candidates)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.session_state.messages.append({"role": "assistant", "content": df, "type": "table"})
                else:
                    # ✅ FIXED: Added candidates argument
                    response = answer_question(
                        st.session_state.vectorstore, 
                        question, 
                        st.session_state.candidates
                    )
                    st.markdown(f"<div class='answer-box'>{response}</div>", unsafe_allow_html=True)
                    st.session_state.messages.append({"role": "assistant", "content": response, "type": "text"})
        
        # Clear trigger
        st.session_state.trigger_question = None
        st.session_state.processing = False
        st.rerun() if hasattr(st, 'rerun') else st.experimental_rerun()
    
    # Chat messages history
    st.subheader("💬 Conversation")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if isinstance(msg["content"], pd.DataFrame):
                st.dataframe(msg["content"], use_container_width=True, hide_index=True)
            else:
                st.markdown(msg["content"])
    
    # Chat input - ✅ FIXED HERE TOO
    if prompt := st.chat_input("Ask about candidates..."):
        if not st.session_state.vectorstore:
            st.warning("⚠️ Process CVs first")
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    if any(kw in prompt.lower() for kw in ["table", "csv", "export", "spreadsheet", "excel"]):
                        df = get_candidates_df(st.session_state.candidates)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.session_state.messages.append({"role": "assistant", "content": df, "type": "table"})
                    else:
                        # ✅ FIXED: Added candidates argument
                        response = answer_question(
                            st.session_state.vectorstore, 
                            prompt, 
                            st.session_state.candidates
                        )
                        st.markdown(f"<div class='answer-box'>{response}</div>", unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": response, "type": "text"})

# ==========================================
# TAB 2: CANDIDATES DATA (Table + Download)
# ==========================================
with tab_data:
    st.subheader("📋 All Candidates Data")
    
    if st.session_state.candidates:
        df = get_candidates_df(st.session_state.candidates)
        
        # Clean column names for display
        df_display = df.rename(columns={
            "name": "Name",
            "phone": "Phone",
            "email": "Email", 
            "current_title": "Title",
            "experience_years": "Experience (Years)",
            "filename": "Source File"
        })
        
        # Display table
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Download button
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name="candidates_data.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Candidates", len(df))
        with col2:
            emails = df[df['email'] != 'N/A']['email'].count()
            st.metric("With Email", emails)
        with col3:
            phones = df[df['phone'] != 'N/A']['phone'].count()
            st.metric("With Phone", phones)
    else:
        st.info("📂 Upload and process CVs to see candidate data here.")

# Footer
st.divider()
st.caption("⚡ Clean Tabs • Text Answers by Default • Data Tab for Tables")