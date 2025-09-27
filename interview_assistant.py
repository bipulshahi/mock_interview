import streamlit as st
import os
from groq import Groq
from dotenv import load_dotenv
import PyPDF2
import docx

# --- Setup ---
st.set_page_config(page_title="AI Interview Coach", layout="centered")
st.title("Mock Interviewer")

# --- Load API key ---
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# --- Initialize state ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a technical interviewer preparing B.Tech CSE students for internships. "
                                      "Always evaluate answers in three steps "
                                      "(1. What’s good, 2. What can be improved, 3. A model answer), "
                                      "and then ask a follow-up question. Tailor questions for B.Tech CSE level."},
        {"role": "assistant", "content": "Let's start! Tell me about yourself."}
    ]
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "input_area" not in st.session_state:
    st.session_state.input_area = ""

# --- Topic selector ---
topic = st.selectbox("Choose interview focus area:", ["General", "DSA", "DBMS", "OOP", "HR", "System Design"])

# --- Resume upload ---
uploaded_resume = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"])
if uploaded_resume:
    if uploaded_resume.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_resume)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        st.session_state.resume_text = text
    elif uploaded_resume.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = docx.Document(uploaded_resume)
        text = "\n".join([para.text for para in doc.paragraphs])
        st.session_state.resume_text = text
    st.success("Resume uploaded and parsed successfully!")

# --- Conversation display (kept below title) ---
st.subheader("Conversation")
for msg in st.session_state.messages[1:]:  # skip system prompt
    if msg["role"] == "assistant":
        st.markdown(f"**Interviewer:** {msg['content']}")
    elif msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")

# --- Clear input helper ---
def clear_input():
    st.session_state.input_area = ""

# --- User input ---
user_input = st.text_area("Your Answer", key="input_area")

# --- Submit button ---
def handle_submit():
    user_input = st.session_state.input_area
    if groq_client and user_input.strip():
        # Add user response
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.spinner("Thinking..."):
            # Add resume + topic context into system prompt dynamically
            context = ""
            if st.session_state.resume_text:
                context += f"\nHere is the candidate's resume:\n{st.session_state.resume_text}\n"
            if topic != "General":
                context += f"\nFocus questions on: {topic}\n"

            st.session_state.messages[0]["content"] = (
                "You are a technical interviewer preparing B.Tech CSE students for internships. "
                "Always evaluate answers in three steps "
                "(1. What’s good, 2. What can be improved, 3. A model answer), "
                "and then ask a follow-up question." + context
            )

            completion = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=st.session_state.messages,
                temperature=0.7,
                max_completion_tokens=1024,
                stream=True
            )

            reply = ""
            placeholder = st.empty()
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    reply += chunk.choices[0].delta.content
                    placeholder.markdown(f"**Interviewer (typing):** {reply}")

            # clear the typing preview once final message is ready
            placeholder.empty()

            # Save final reply into conversation
            st.session_state.messages.append({"role": "assistant", "content": reply})

        # clear input after processing
        clear_input()
    else:
        st.warning("Please enter an answer (and check your GROQ_API_KEY).")

st.button("Submit Answer", on_click=handle_submit)

# --- Download transcript ---
if st.button("Download Transcript (TXT)"):
    transcript = "\n".join([
        f"{'Interviewer' if m['role']=='assistant' else 'You'}: {m['content']}"
        for m in st.session_state.messages[1:]  # skip system prompt
    ])
    st.download_button("Download Now", transcript, "interview_transcript.txt")
