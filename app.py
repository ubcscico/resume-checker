import os
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document

# 1. Title of your web page
st.title("AI Resume Checker")
st.write("Upload your resume and paste the job description to find out where your resume is weak.")

# 2. File uploader box for the resume
uploaded_file = st.file_uploader("Upload your resume (PDF or Word)", type=["pdf", "docx"])

# 3. Text box for the job description
job_description = st.text_area("Paste the Job Description here:")

# 4. The magic button
if st.button("Analyze Resume"):
    if not uploaded_file:
        st.warning("Please upload a resume first.")
    elif not job_description:
        st.warning("Please paste a job description.")
    else:
        try:
            # Extract text from uploaded file
            text = ""
            if uploaded_file.name.endswith(".pdf"):
                reader = PdfReader(uploaded_file)
                for page in reader.pages:
                    text += page.extract_text() or ""
            else:
                doc = Document(uploaded_file)
                for para in doc.paragraphs:
                    text += para.text + "\n"

            # Initialize Gemini Client with API key from secrets
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

            prompt = f"""
            You are an expert technical recruiter and hiring manager. 
            Analyze the following resume against the provided job description. 
            
            Provide a detailed critique with the following sections:
            1. **Match Score:** An estimated percentage match (0-100%).
            2. **Key Strengths:** Where the candidate strongly aligns with the role.
            3. **Weaknesses & Gaps:** Missing hard skills, experience gaps, or weak impact statements.
            4. **Missing Keywords:** Critical technical terms or industry keywords present in the job description but absent from the resume.
            5. **Actionable Recommendations:** Specific bullet points on how to rewrite sections to improve the resume.

            ---
            JOB DESCRIPTION:
            {job_description}

            ---
            RESUME:
            {text}
            """

            st.subheader("Analysis Results")
            
            # Helper generator to stream text safely with automatic model fallback
            def generate_stream():
                models_to_try = ['gemini-3.8-flash', 'gemini-3.5-flash-lite']
                for model_name in models_to_try:
                    try:
                        response = client.models.generate_content_stream(
                            model=model_name,
                            contents=prompt,
                        )
                        for chunk in response:
                            if chunk.text:
                                yield chunk.text
                        return  # Success: exit once streaming finishes
                    except Exception as err:
                        # If model is overloaded (503), try the next model
                        if "503" in str(err) or "service_unavailable" in str(err):
                            st.info(f"Primary model busy, switching to high-speed backup ({model_name} -> gemini-3.5-flash-lite)...")
                            continue
                        else:
                            raise err

            st.write_stream(generate_stream)

        except Exception as e:
            st.error(f"An error occurred: {e}")
