import os
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document

# 1. Title of your web page
st.title("AI Resume Checker")
st.write("Upload your resume, paste the job description, and provide company details to find out where your resume is weak.")

# 2. File uploader box for the resume
uploaded_file = st.file_uploader("Upload your resume (PDF or Word)", type=["pdf", "docx"])

# 3. Company input box
company_info = st.text_input("Target Company Name or Website (Optional):")

# 4. Text box for the job description
job_description = st.text_area("Paste the Job Description here:")

# 5. The magic button
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
            You are an expert technical recruiter, hiring manager, and career coach. 
            Analyze the following resume against the provided job description for the company/organization: {company_info if company_info else "General Industry"}. 
            
            Provide a detailed critique using clear Markdown headings (using standard markdown ### prefixes) with the following structure:
            
            ### Match Score
            An estimated percentage match (0-100%) followed by a brief summary overview paragraph.
            
            ### Key Strengths
            Where the candidate strongly aligns with the role and company context.
            
            ### Weaknesses and Gaps
            Missing hard skills, experience gaps, or weak impact statements.
            
            ### Missing Keywords
            Critical technical terms or industry keywords present in the job description or typical for this role/company but absent from the resume.
            
            ### Cover Letter Focus Points
            The major skills, technical experiences, and key requirements from the job description that the student should explicitly emphasize and weave into their cover letter.
            
            ### Actionable Recommendations
            Specific bullet points on how to rewrite sections to improve the resume.

            ---
            COMPANY CONTEXT:
            {company_info if company_info else "Not specified"}

            ---
            JOB DESCRIPTION:
            {job_description}

            ---
            RESUME:
            {text}
            """

            st.subheader("Analysis Results")
            
            results_container = st.empty()

            # Helper generator to stream text safely with automatic model fallback
            def generate_stream():
                models_to_try = ['gemini-3.8-flash', 'gemini-3.5-flash-lite']
                for model_name in models_to_try:
                    try:
                        response = client.models.generate_content_stream(
                            model=model_name,
                            contents=prompt,
                        )
                        full_response = ""
                        for chunk in response:
                            if chunk.text:
                                full_response += chunk.text
                                results_container.markdown(full_response)
                        return full_response
                    except Exception as err:
                        if "503" in str(err) or "service_unavailable" in str(err):
                            continue
                        else:
                            raise err

            generate_stream()

        except Exception as e:
            st.error(f"An error occurred: {e}")
