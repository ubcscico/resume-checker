import os
import streamlit as st
from google import genai
from pypdf import PdfReader
from docx import Document
import streamlit.components.v1 as components

# 1. Title of your web page
st.title("AI Resume Checker")
st.write("Upload your resume, paste the job description, and provide company details to find out where your resume is weak.")

# 2. File uploader box for the resume
uploaded_file = st.file_uploader("Upload your resume (PDF or Word)", type=["pdf", "docx"])

# 3. Company input box
company_info = st.text_input("Target Company Name or Website (Optional):")

# 4. Text box for the job description
job_description = st.text_area("Paste the Job Description here:")

# Helper function to render a styled neon blue copy button using raw HTML/JS
def render_copy_button(position_label):
    copy_html = f"""
    <div style="margin: 10px 0;">
        <button onclick="copyAnalysis()" style="
            background-color: #00d2ff;
            color: #0e1117;
            border: none;
            padding: 9px 18px;
            font-size: 14px;
            font-weight: bold;
            border-radius: 6px;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 0 12px rgba(0, 210, 255, 0.4);
            transition: background 0.2s ease;">
            📋 Copy Entire Analysis ({position_label})
        </button>
        <span id="copy-status-{position_label}" style="margin-left: 10px; font-size: 12px; color: #00d2ff; font-family: sans-serif; font-weight: bold;"></span>
    </div>

    <script>
    function copyAnalysis() {{
        // Finds the results container on the page dynamically
        const resultsBox = document.getElementById('analysis-results-box');
        if (resultsBox) {{
            const textToCopy = resultsBox.innerText;
            navigator.clipboard.writeText(textToCopy).then(() => {{
                const statusSpan = document.getElementById('copy-status-{position_label}');
                statusSpan.innerText = "Copied to clipboard!";
                setTimeout(() => {{ statusSpan.innerText = ""; }}, 3000);
            }}).catch(err => {{
                alert('Failed to copy: ' + err);
            }});
        }} else {{
            alert('No analysis results found to copy yet!');
        }}
    }}
    </script>
    """
    components.html(copy_html, height=50)

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
            You are an expert technical recruiter and hiring manager. 
            Analyze the following resume against the provided job description for the company/organization: {company_info if company_info else "General Industry"}. 
            
            Provide a detailed critique with the following sections:
            1. **Match Score:** An estimated percentage match (0-100%).
            2. **Key Strengths:** Where the candidate strongly aligns with the role and company context.
            3. **Weaknesses & Gaps:** Missing hard skills, experience gaps, or weak impact statements.
            4. **Missing Keywords:** Critical technical terms or industry keywords present in the job description or typical for this role/company but absent from the resume.
            5. **Actionable Recommendations:** Specific bullet points on how to rewrite sections to improve the resume.

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
            
            # TOP COPY BUTTON
            render_copy_button("Top")

            # We wrap the results inside a designated HTML container with an ID
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
                                # Update container live as it streams
                                results_container.markdown(f'<div id="analysis-results-box">{full_response}</div>', unsafe_allow_html=True)
                        return  # Success: exit once streaming finishes
                    except Exception as err:
                        if "503" in str(err) or "service_unavailable" in str(err):
                            continue
                        else:
                            raise err

            generate_stream()

            # BOTTOM COPY BUTTON
            render_copy_button("Bottom")

        except Exception as e:
            st.error(f"An error occurred: {e}")
