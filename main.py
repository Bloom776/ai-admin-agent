# main.py
import streamlit as st
from agents.calendar_agent_streamlit import calendar_agent_menu_streamlit
from agents.email_agent import email_agent_menu
from agents.doc_agent import (
    get_transcript, summarize_meeting, draft_follow_up_email,
    extract_tasks_from_summary, generate_pre_call_brief
)

st.set_page_config(page_title="Agent Dashboard", layout="wide")
st.title("🤖 Admin Agent Dashboard")

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Choose an Agent", ["📅 Calendar", "📧 Email", "📄 Docs"])

# Calendar Agent
if page == "📅 Calendar":
    calendar_agent_menu_streamlit()
# Email Agent
elif page == "📧 Email":
    st.header("Email Agent")
    email_agent_menu()

# Docs Agent
elif page == "📄 Docs":
    st.header("Docs Agent")
    provider = st.selectbox("Transcript Provider", ["manual", "otter", "zoom"])
    transcript_text = st.text_area("Paste Transcript", "")

    if st.button("Summarize"):
        transcript = get_transcript(provider, transcript_text=transcript_text)
        summary = summarize_meeting(transcript)
        st.subheader("Meeting Summary")
        st.write(summary)

        tasks = extract_tasks_from_summary(summary)
        st.subheader("Action Items")
        st.write(tasks)

        followup = draft_follow_up_email("Jane Doe", summary, tasks)
        st.subheader("Follow-Up Email Draft")
        st.write(followup)

