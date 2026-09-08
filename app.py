# app.py - Updated with External LLM Support
import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import snowflake.connector
from datetime import datetime
import PyPDF2
import docx
import io
import time
import os
import ssl
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# LLM PROVIDER SETUP
# ============================================================

class LLMProvider:
    """Handles AI calls to different providers"""
    
    def __init__(self):
        self.provider = self._detect_provider()
    
    def _detect_provider(self):
        """Detect which LLM provider is configured"""
        if "groq" in st.secrets and st.secrets["groq"].get("api_key"):
            return "groq"
        elif "openai" in st.secrets and st.secrets["openai"].get("api_key"):
            return "openai"
        elif "ollama" in st.secrets:
            return "ollama"
        else:
            return None
    
    def complete(self, prompt, temperature=0.3):
        """Call the configured LLM provider"""
        if self.provider == "groq":
            return self._call_groq(prompt, temperature)
        elif self.provider == "openai":
            return self._call_openai(prompt, temperature)
        elif self.provider == "ollama":
            return self._call_ollama(prompt, temperature)
        else:
            st.error("No LLM provider configured! Please add API keys to secrets.toml")
            return None
    
    def _call_groq(self, prompt, temperature):
        """Call Groq API (FREE)"""
        from groq import Groq
        client = Groq(api_key=st.secrets["groq"]["api_key"])
        
        response = client.chat.completions.create(
            model=st.secrets["groq"].get("model", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": "You are an expert technical recruiter and resume screener. Always respond in valid JSON format when asked."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    
    def _call_openai(self, prompt, temperature):
        """Call OpenAI API"""
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        
        response = client.chat.completions.create(
            model=st.secrets["openai"].get("model", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are an expert technical recruiter and resume screener. Always respond in valid JSON format when asked."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    
    def _call_ollama(self, prompt, temperature):
        """Call local Ollama"""
        import requests
        
        base_url = st.secrets["ollama"].get("base_url", "http://localhost:11434")
        model = st.secrets["ollama"].get("model", "llama3.1")
        
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "stream": False,
                "format": "json"
            }
        )
        return response.json()["response"]


# Initialize LLM
@st.cache_resource
def get_llm():
    return LLMProvider()


# ============================================================
# SNOWFLAKE CONNECTION (Storage Only)
# ============================================================

@st.cache_resource
def get_snowflake_connection():
    """Create Snowflake connection"""
    conn = snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"]
    )
    return conn


def run_query(query, params=None):
    """Execute query and return DataFrame"""
    conn = get_snowflake_connection()
    try:
        if params:
            df = pd.read_sql(query, conn, params=params)
        else:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Query error: {e}")
        return pd.DataFrame()


def execute_query(query, params=None):
    """Execute INSERT/UPDATE/DELETE"""
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
    except Exception as e:
        st.error(f"Execution error: {e}")
    finally:
        cursor.close()


# ============================================================
# AI SCREENING FUNCTIONS
# ============================================================

def screen_candidate(job_data, candidate_data, llm):
    """Screen a single candidate against a job description using external LLM"""
    
    prompt = f"""Analyze this candidate's profile against the job description. 
Score each criteria from 0 to 100 and provide your assessment.

## JOB DESCRIPTION:
Title: {job_data['JOB_TITLE']}
Description: {job_data['JOB_DESCRIPTION']}
Required Skills: {job_data['REQUIRED_SKILLS']}
Preferred Skills: {job_data.get('PREFERRED_SKILLS', 'None specified')}
Minimum Experience: {job_data['MIN_EXPERIENCE_YEARS']} years
Maximum Experience: {job_data['MAX_EXPERIENCE_YEARS']} years
Education Required: {job_data.get('EDUCATION_REQUIREMENT', 'Not specified')}

## CANDIDATE PROFILE:
Name: {candidate_data['FULL_NAME']}
Current Title: {candidate_data.get('CURRENT_TITLE', 'Not specified')}
Experience: {candidate_data.get('TOTAL_EXPERIENCE_YEARS', 0)} years
Skills: {candidate_data.get('SKILLS', 'Not specified')}
Education: {candidate_data.get('EDUCATION', 'Not specified')}
Certifications: {candidate_data.get('CERTIFICATIONS', 'None')}

Resume Content:
{candidate_data.get('RESUME_TEXT', 'Not available')[:3000]}

## SCORING CRITERIA:
1. **skills_match_score** (0-100): How well do the candidate's skills match required & preferred skills?
2. **experience_match_score** (0-100): Does experience level fit the range? Is the experience relevant?
3. **education_match_score** (0-100): Does education meet requirements?
4. **keyword_match_score** (0-100): How many job-specific keywords appear in the resume?
5. **culture_fit_score** (0-100): Based on career progression, stability, and role alignment
6. **overall_score** (0-100): Weighted average considering all factors

## RESPOND IN THIS EXACT JSON FORMAT:
{{
    "overall_score": <number>,
    "skills_match_score": <number>,
    "experience_match_score": <number>,
    "education_match_score": <number>,
    "keyword_match_score": <number>,
    "culture_fit_score": <number>,
    "summary": "<2-3 sentence professional assessment>",
    "strengths": "<comma-separated top 3-5 strengths>",
    "gaps": "<comma-separated gaps or concerns>",
    "recommendation": "<STRONG_MATCH|GOOD_MATCH|MODERATE_MATCH|WEAK_MATCH|NOT_SUITABLE>",
    "matching_skills": "<comma-separated skills that match the JD>",
    "missing_skills": "<comma-separated required skills the candidate lacks>"
}}"""
    
    response = llm.complete(prompt)
    
    if response:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
    return None


def extract_resume_info(resume_text, llm):
    """Extract structured info from resume using LLM"""
    
    prompt = f"""Extract the following information from this resume. 
If information is not available, use empty string or 0.

Resume:
{resume_text[:4000]}

Respond in this exact JSON format:
{{
    "full_name": "",
    "email": "",
    "phone": "",
    "total_experience_years": 0,
    "current_title": "",
    "current_company": "",
    "skills": "",
    "education": "",
    "certifications": "",
    "summary": ""
}}"""
    
    response = llm.complete(prompt)
    
    if response:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return None
    return None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF"""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(docx_file):
    """Extract text from DOCX"""
    doc = docx.Document(docx_file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


def extract_text_from_file(uploaded_file):
    """Extract text based on file type"""
    if uploaded_file.type == "application/pdf":
        return extract_text_from_pdf(uploaded_file)
    elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        return extract_text_from_docx(uploaded_file)
    elif uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    return None


def get_recommendation_color(recommendation):
    """Return color for recommendation"""
    colors = {
        "STRONG_MATCH": "#28a745",
        "GOOD_MATCH": "#17a2b8",
        "MODERATE_MATCH": "#ffc107",
        "WEAK_MATCH": "#fd7e14",
        "NOT_SUITABLE": "#dc3545"
    }
    return colors.get(recommendation, "#6c757d")


# ============================================================
# MAIN APP
# ============================================================

# Initialize
llm = get_llm()

# Custom CSS
st.markdown("""
<style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .success-badge { background-color: #28a745; color: white; padding: 5px 15px; border-radius: 20px; }
    .warning-badge { background-color: #ffc107; color: black; padding: 5px 15px; border-radius: 20px; }
    .danger-badge { background-color: #dc3545; color: white; padding: 5px 15px; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("## 🎯 AI Resume Screener")
st.sidebar.markdown("---")

if llm.provider:
    st.sidebar.success(f"✅ LLM: {llm.provider.upper()}")
else:
    st.sidebar.error("❌ No LLM configured")

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "📋 Job Descriptions", "👤 Candidates", 
     "🔍 Screen Candidates", "📊 Rankings", "⚙️ Settings"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Snowflake (Storage) + External AI (Screening)")


# ==================== DASHBOARD ====================
if page == "🏠 Dashboard":
    st.markdown("# 🎯 AI-Powered Resume Screening")
    st.markdown("*Intelligent candidate ranking using AI*")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        df = run_query("SELECT COUNT(*) as CNT FROM JOB_DESCRIPTIONS WHERE STATUS = 'ACTIVE'")
        st.metric("Active Jobs", df['CNT'].iloc[0] if not df.empty else 0)
    with col2:
        df = run_query("SELECT COUNT(*) as CNT FROM CANDIDATE_PROFILES")
        st.metric("Candidates", df['CNT'].iloc[0] if not df.empty else 0)
    with col3:
        df = run_query("SELECT COUNT(*) as CNT FROM SCREENING_RESULTS")
        st.metric("Screenings", df['CNT'].iloc[0] if not df.empty else 0)
    with col4:
        df = run_query("SELECT COALESCE(AVG(OVERALL_SCORE), 0) as AVG FROM SCREENING_RESULTS")
        st.metric("Avg Score", f"{df['AVG'].iloc[0]:.1f}%" if not df.empty else "0%")
    
    st.markdown("---")
    
    # Recent results
    st.subheader("📈 Recent Screenings")
    recent = run_query("""
        SELECT cp.FULL_NAME, jd.JOB_TITLE, sr.OVERALL_SCORE, 
               sr.RECOMMENDATION, sr.SCREENED_AT
        FROM SCREENING_RESULTS sr
        JOIN CANDIDATE_PROFILES cp ON sr.CANDIDATE_ID = cp.CANDIDATE_ID
        JOIN JOB_DESCRIPTIONS jd ON sr.JOB_ID = jd.JOB_ID
        ORDER BY sr.SCREENED_AT DESC LIMIT 10
    """)
    
    if not recent.empty:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("No screenings yet. Start by adding jobs and candidates!")


# ==================== JOB DESCRIPTIONS ====================
elif page == "📋 Job Descriptions":
    st.markdown("## 📋 Job Descriptions")
    
    tab1, tab2 = st.tabs(["➕ Add New Job", "📄 View Jobs"])
    
    with tab1:
        with st.form("new_job"):
            col1, col2 = st.columns(2)
            with col1:
                job_title = st.text_input("Job Title *", placeholder="Senior Data Engineer")
                department = st.text_input("Department", placeholder="Engineering")
                location = st.text_input("Location", placeholder="Remote")
                employment_type = st.selectbox("Type", ["Full-time", "Part-time", "Contract"])
            with col2:
                min_exp = st.number_input("Min Experience (years)", 0, 30, 3)
                max_exp = st.number_input("Max Experience (years)", 0, 30, 7)
                education_req = st.text_input("Education", placeholder="B.Tech in CS")
            
            job_description = st.text_area("Job Description *", height=200)
            required_skills = st.text_area("Required Skills *", placeholder="Python, SQL, AWS, Spark")
            preferred_skills = st.text_area("Preferred Skills", placeholder="Kubernetes, dbt, Snowflake")
            
            if st.form_submit_button("Create Job", type="primary"):
                if job_title and job_description and required_skills:
                    execute_query("""
                        INSERT INTO JOB_DESCRIPTIONS 
                        (JOB_TITLE, DEPARTMENT, JOB_DESCRIPTION, REQUIRED_SKILLS,
                         PREFERRED_SKILLS, MIN_EXPERIENCE_YEARS, MAX_EXPERIENCE_YEARS,
                         EDUCATION_REQUIREMENT, LOCATION, EMPLOYMENT_TYPE)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (job_title, department, job_description, required_skills,
                          preferred_skills, min_exp, max_exp, education_req,
                          location, employment_type))
                    st.success(f"✅ Job '{job_title}' created!")
                    st.balloons()
                else:
                    st.error("Please fill required fields (*)")
    
    with tab2:
        jobs = run_query("SELECT * FROM JOB_DESCRIPTIONS WHERE STATUS = 'ACTIVE' ORDER BY CREATED_AT DESC")
        if not jobs.empty:
            for _, job in jobs.iterrows():
                with st.expander(f"🔹 {job['JOB_TITLE']} | {job['DEPARTMENT']} | {job['LOCATION']}"):
                    st.write(f"**Experience:** {job['MIN_EXPERIENCE_YEARS']}-{job['MAX_EXPERIENCE_YEARS']} years")
                    st.write(f"**Required Skills:** {job['REQUIRED_SKILLS']}")
                    st.write(f"**Description:** {job['JOB_DESCRIPTION'][:500]}...")
        else:
            st.info("No active jobs. Create one above!")


# ==================== CANDIDATES ====================
elif page == "👤 Candidates":
    st.markdown("## 👤 Candidate Profiles")
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload Resumes", "✍️ Manual Entry", "👁️ View All"])
    
    with tab1:
        uploaded_files = st.file_uploader(
            "Upload Resumes (PDF, DOCX, TXT)", 
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True
        )
        
        if uploaded_files and st.button("🔄 Process Resumes", type="primary"):
            progress = st.progress(0)
            
            for idx, file in enumerate(uploaded_files):
                with st.spinner(f"Processing {file.name}..."):
                    resume_text = extract_text_from_file(file)
                    
                    if resume_text:
                        # Use LLM to extract info
                        extracted = extract_resume_info(resume_text, llm)
                        
                        if extracted:
                            execute_query("""
                                INSERT INTO CANDIDATE_PROFILES 
                                (FULL_NAME, EMAIL, PHONE, TOTAL_EXPERIENCE_YEARS,
                                 CURRENT_TITLE, CURRENT_COMPANY, SKILLS, EDUCATION,
                                 CERTIFICATIONS, RESUME_TEXT, RESUME_SUMMARY)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                extracted.get('full_name', file.name.split('.')[0]),
                                extracted.get('email', ''),
                                extracted.get('phone', ''),
                                float(extracted.get('total_experience_years', 0)),
                                extracted.get('current_title', ''),
                                extracted.get('current_company', ''),
                                extracted.get('skills', ''),
                                extracted.get('education', ''),
                                extracted.get('certifications', ''),
                                resume_text,
                                extracted.get('summary', '')
                            ))
                            st.success(f"✅ {extracted.get('full_name', file.name)}")
                        else:
                            # Save raw text
                            execute_query("""
                                INSERT INTO CANDIDATE_PROFILES (FULL_NAME, RESUME_TEXT)
                                VALUES (%s, %s)
                            """, (file.name.split('.')[0], resume_text))
                            st.warning(f"⚠️ Saved {file.name} with limited extraction")
                    else:
                        st.error(f"❌ Could not read {file.name}")
                
                progress.progress((idx + 1) / len(uploaded_files))
                
                # Rate limiting for free APIs
                if llm.provider == "groq":
                    time.sleep(2)  # Respect rate limits
            
            st.success("🎉 All files processed!")
    
    with tab2:
        with st.form("manual_candidate"):
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name *")
                email = st.text_input("Email")
                phone = st.text_input("Phone")
                experience = st.number_input("Experience (years)", 0.0, 50.0, 3.0, 0.5)
            with col2:
                current_title = st.text_input("Current Title")
                current_company = st.text_input("Current Company")
                education = st.text_input("Education")
                certifications = st.text_input("Certifications")
            
            skills = st.text_area("Skills", placeholder="Python, Java, SQL, AWS...")
            resume_text = st.text_area("Resume/Profile Text", height=200)
            
            if st.form_submit_button("Add Candidate", type="primary"):
                if full_name:
                    execute_query("""
                        INSERT INTO CANDIDATE_PROFILES 
                        (FULL_NAME, EMAIL, PHONE, TOTAL_EXPERIENCE_YEARS,
                         CURRENT_TITLE, CURRENT_COMPANY, SKILLS, EDUCATION,
                         CERTIFICATIONS, RESUME_TEXT)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (full_name, email, phone, experience, current_title,
                          current_company, skills, education, certifications, resume_text))
                    st.success(f"✅ Added {full_name}")
    
    with tab3:
        candidates = run_query("""
            SELECT CANDIDATE_ID, FULL_NAME, EMAIL, CURRENT_TITLE, 
                   CURRENT_COMPANY, TOTAL_EXPERIENCE_YEARS, SKILLS, UPLOADED_AT
            FROM CANDIDATE_PROFILES ORDER BY UPLOADED_AT DESC LIMIT 100
        """)
        if not candidates.empty:
            st.dataframe(candidates, use_container_width=True, hide_index=True)
        else:
            st.info("No candidates yet.")


# ==================== SCREEN CANDIDATES ====================
elif page == "🔍 Screen Candidates":
    st.markdown("## 🔍 AI Screening")
    
    if not llm.provider:
        st.error("❌ No LLM provider configured. Please add API keys to .streamlit/secrets.toml")
        st.stop()
    
    tab1, tab2 = st.tabs(["🎯 Individual Screening", "🚀 Bulk Screening"])
    
    with tab1:
        jobs = run_query("SELECT JOB_ID, JOB_TITLE, DEPARTMENT FROM JOB_DESCRIPTIONS WHERE STATUS = 'ACTIVE'")
        candidates = run_query("SELECT CANDIDATE_ID, FULL_NAME, CURRENT_TITLE FROM CANDIDATE_PROFILES")
        
        if jobs.empty or candidates.empty:
            st.warning("Need at least 1 job and 1 candidate to screen.")
            st.stop()
        
        col1, col2 = st.columns(2)
        with col1:
            job_options = jobs.apply(lambda x: f"{x['JOB_TITLE']} ({x['DEPARTMENT']})", axis=1).tolist()
            selected_job = st.selectbox("Select Job", job_options)
            job_idx = job_options.index(selected_job)
            job_id = jobs.iloc[job_idx]['JOB_ID']
        
        with col2:
            cand_options = candidates.apply(lambda x: f"{x['FULL_NAME']} - {x['CURRENT_TITLE']}", axis=1).tolist()
            selected_cand = st.selectbox("Select Candidate", cand_options)
            cand_idx = cand_options.index(selected_cand)
            candidate_id = candidates.iloc[cand_idx]['CANDIDATE_ID']
        
        if st.button("🔍 Run AI Screening", type="primary"):
            with st.spinner("🤖 AI is analyzing the profile..."):
                # Fetch full data
                job_data = run_query(
                    "SELECT * FROM JOB_DESCRIPTIONS WHERE JOB_ID = %s", 
                    (job_id,)
                ).iloc[0].to_dict()
                
                candidate_data = run_query(
                    "SELECT * FROM CANDIDATE_PROFILES WHERE CANDIDATE_ID = %s",
                    (candidate_id,)
                ).iloc[0].to_dict()
                
                # AI Screening
                result = screen_candidate(job_data, candidate_data, llm)
                
                if result:
                    # Save to Snowflake
                    execute_query("""
                        INSERT INTO SCREENING_RESULTS 
                        (JOB_ID, CANDIDATE_ID, OVERALL_SCORE, SKILLS_MATCH_SCORE,
                         EXPERIENCE_MATCH_SCORE, EDUCATION_MATCH_SCORE, KEYWORD_MATCH_SCORE,
                         CULTURE_FIT_SCORE, AI_SUMMARY, STRENGTHS, GAPS, RECOMMENDATION, SCREENED_BY)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        job_id, candidate_id,
                        result.get('overall_score', 0),
                        result.get('skills_match_score', 0),
                        result.get('experience_match_score', 0),
                        result.get('education_match_score', 0),
                        result.get('keyword_match_score', 0),
                        result.get('culture_fit_score', 0),
                        result.get('summary', ''),
                        result.get('strengths', ''),
                        result.get('gaps', ''),
                        result.get('recommendation', 'N/A'),
                        'AI Screener'
                    ))
                    
                    st.success("✅ Screening Complete!")
                    st.markdown("---")
                    
                    # Display Results
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.metric("Overall Score", f"{result['overall_score']}/100")
                        rec = result.get('recommendation', 'N/A')
                        color = get_recommendation_color(rec)
                        st.markdown(
                            f'<span style="background-color:{color};color:white;padding:8px 16px;'
                            f'border-radius:20px;font-weight:bold;">{rec.replace("_", " ")}</span>',
                            unsafe_allow_html=True
                        )
                    
                    with col2:
                        scores = {
                            "Skills": result.get('skills_match_score', 0),
                            "Experience": result.get('experience_match_score', 0),
                            "Education": result.get('education_match_score', 0),
                            "Keywords": result.get('keyword_match_score', 0),
                            "Culture Fit": result.get('culture_fit_score', 0),
                        }
                        
                        fig = go.Figure(data=go.Scatterpolar(
                            r=list(scores.values()),
                            theta=list(scores.keys()),
                            fill='toself',
                            fillcolor='rgba(30, 58, 95, 0.3)',
                            line=dict(color='#1E3A5F', width=2)
                        ))
                        fig.update_layout(
                            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                            showlegend=False, height=350
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Details
                    col_s, col_g = st.columns(2)
                    with col_s:
                        st.markdown("#### 💪 Strengths")
                        st.success(result.get('strengths', 'N/A'))
                        if result.get('matching_skills'):
                            st.markdown(f"**Matching Skills:** {result['matching_skills']}")
                    with col_g:
                        st.markdown("#### ⚠️ Gaps")
                        st.warning(result.get('gaps', 'N/A'))
                        if result.get('missing_skills'):
                            st.markdown(f"**Missing Skills:** {result['missing_skills']}")
                    
                    st.markdown("#### 📝 AI Assessment")
                    st.info(result.get('summary', 'N/A'))
                else:
                    st.error("❌ AI screening failed. Please try again.")
    
    with tab2:
        st.subheader("🚀 Bulk Screening")
        
        jobs = run_query("SELECT JOB_ID, JOB_TITLE, DEPARTMENT FROM JOB_DESCRIPTIONS WHERE STATUS = 'ACTIVE'")
        
        if not jobs.empty:
            job_options = jobs.apply(lambda x: f"{x['JOB_TITLE']} ({x['DEPARTMENT']})", axis=1).tolist()
            selected_bulk_job = st.selectbox("Select Job for Bulk Screening", job_options, key="bulk")
            job_idx = job_options.index(selected_bulk_job)
            bulk_job_id = jobs.iloc[job_idx]['JOB_ID']
            
            # Unscreened candidates
            unscreened = run_query("""
                SELECT cp.CANDIDATE_ID, cp.FULL_NAME, cp.CURRENT_TITLE
                FROM CANDIDATE_PROFILES cp
                WHERE cp.CANDIDATE_ID NOT IN (
                    SELECT CANDIDATE_ID FROM SCREENING_RESULTS WHERE JOB_ID = %s
                )
            """, (bulk_job_id,))
            
            st.write(f"**{len(unscreened)} candidates** pending screening")
            
            # Parallel limit based on provider
            rate_limits = {
                "groq": {"max_parallel": 10, "delay": 3, "note": "Free tier: 30 req/min"},
                "openai": {"max_parallel": 50, "delay": 0.5, "note": "Paid: high throughput"},
                "ollama": {"max_parallel": 5, "delay": 1, "note": "Local: depends on hardware"}
            }
            
            provider_limits = rate_limits.get(llm.provider, {"max_parallel": 5, "delay": 2, "note": ""})
            
            st.info(f"**LLM Provider:** {llm.provider.upper()} | {provider_limits['note']}")
            
            batch_size = st.slider(
                "Batch Size", 
                1, 
                min(provider_limits['max_parallel'], len(unscreened)) if not unscreened.empty else 1,
                min(5, len(unscreened)) if not unscreened.empty else 1
            )
            
            if not unscreened.empty and st.button("🚀 Start Bulk Screening", type="primary"):
                # Get job data
                job_data = run_query(
                    "SELECT * FROM JOB_DESCRIPTIONS WHERE JOB_ID = %s", (bulk_job_id,)
                ).iloc[0].to_dict()
                
                progress = st.progress(0)
                status = st.empty()
                results_container = st.container()
                
                batch_results = []
                
                for idx, (_, candidate_row) in enumerate(unscreened.head(batch_size).iterrows()):
                    status.text(f"Screening {candidate_row['FULL_NAME']}... ({idx+1}/{batch_size})")
                    
                    # Get full candidate data
                    candidate_data = run_query(
                        "SELECT * FROM CANDIDATE_PROFILES WHERE CANDIDATE_ID = %s",
                        (candidate_row['CANDIDATE_ID'],)
                    ).iloc[0].to_dict()
                    
                    # Screen
                    result = screen_candidate(job_data, candidate_data, llm)
                    
                    if result:
                        # Save to DB
                        execute_query("""
                            INSERT INTO SCREENING_RESULTS 
                            (JOB_ID, CANDIDATE_ID, OVERALL_SCORE, SKILLS_MATCH_SCORE,
                             EXPERIENCE_MATCH_SCORE, EDUCATION_MATCH_SCORE, KEYWORD_MATCH_SCORE,
                             CULTURE_FIT_SCORE, AI_SUMMARY, STRENGTHS, GAPS, RECOMMENDATION, SCREENED_BY)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            bulk_job_id, candidate_row['CANDIDATE_ID'],
                            result.get('overall_score', 0),
                            result.get('skills_match_score', 0),
                            result.get('experience_match_score', 0),
                            result.get('education_match_score', 0),
                            result.get('keyword_match_score', 0),
                            result.get('culture_fit_score', 0),
                            result.get('summary', ''),
                            result.get('strengths', ''),
                            result.get('gaps', ''),
                            result.get('recommendation', 'N/A'),
                            'Bulk AI Screener'
                        ))
                        
                        batch_results.append({
                            'Name': candidate_row['FULL_NAME'],
                            'Score': result['overall_score'],
                            'Recommendation': result.get('recommendation', 'N/A')
                        })
                    else:
                        batch_results.append({
                            'Name': candidate_row['FULL_NAME'],
                            'Score': 'Failed',
                            'Recommendation': 'ERROR'
                        })
                    
                    progress.progress((idx + 1) / batch_size)
                    
                    # Rate limiting
                    time.sleep(provider_limits['delay'])
                
                status.text("✅ Bulk screening complete!")
                
                # Show results
                with results_container:
                    results_df = pd.DataFrame(batch_results)
                    results_df = results_df.sort_values('Score', ascending=False)
                    st.dataframe(results_df, use_container_width=True, hide_index=True)


# ==================== RANKINGS ====================
elif page == "📊 Rankings":
    st.markdown("## 📊 Candidate Rankings")
    
    jobs = run_query("SELECT JOB_ID, JOB_TITLE, DEPARTMENT FROM JOB_DESCRIPTIONS WHERE STATUS = 'ACTIVE'")
    
    if not jobs.empty:
        job_options = jobs.apply(lambda x: f"{x['JOB_TITLE']} ({x['DEPARTMENT']})", axis=1).tolist()
        selected_rank_job = st.selectbox("Select Job", job_options, key="rankings")
        job_idx = job_options.index(selected_rank_job)
        rank_job_id = jobs.iloc[job_idx]['JOB_ID']
        
        rankings = run_query("""
            SELECT 
                ROW_NUMBER() OVER (ORDER BY sr.OVERALL_SCORE DESC) as RANK,
                cp.FULL_NAME,
                cp.CURRENT_TITLE,
                cp.TOTAL_EXPERIENCE_YEARS as EXP_YEARS,
                sr.OVERALL_SCORE,
                sr.SKILLS_MATCH_SCORE,
                sr.EXPERIENCE_MATCH_SCORE,
                sr.EDUCATION_MATCH_SCORE,
                sr.KEYWORD_MATCH_SCORE,
                sr.CULTURE_FIT_SCORE,
                sr.RECOMMENDATION,
                sr.AI_SUMMARY,
                sr.STRENGTHS,
                sr.GAPS
            FROM SCREENING_RESULTS sr
            JOIN CANDIDATE_PROFILES cp ON sr.CANDIDATE_ID = cp.CANDIDATE_ID
            WHERE sr.JOB_ID = %s
            ORDER BY sr.OVERALL_SCORE DESC
        """, (rank_job_id,))
        
        if not rankings.empty:
            st.write(f"**{len(rankings)} candidates ranked**")
            
            # Top candidates chart
            fig = go.Figure()
            top_10 = rankings.head(10)
            fig.add_trace(go.Bar(name='Overall', x=top_10['FULL_NAME'], y=top_10['OVERALL_SCORE'],
                                marker_color='#1E3A5F'))
            fig.update_layout(title='Top 10 Candidates', xaxis_tickangle=-45, height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed table
            st.dataframe(
                rankings[['RANK', 'FULL_NAME', 'CURRENT_TITLE', 'EXP_YEARS', 
                          'OVERALL_SCORE', 'RECOMMENDATION']],
                use_container_width=True, hide_index=True
            )
            
            # Export
            csv = rankings.to_csv(index=False)
            st.download_button("📥 Download Full Report (CSV)", csv,
                             f"rankings_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        else:
            st.info("No screening results for this job yet.")
    else:
        st.info("No active jobs found.")


# ==================== SETTINGS ====================
elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Settings")
    
    st.subheader("🔌 Connection Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Snowflake")
        try:
            test = run_query("SELECT CURRENT_ACCOUNT() as ACCOUNT, CURRENT_USER() as USER_NAME")
            st.success(f"✅ Connected to: {test['ACCOUNT'].iloc[0]}")
            st.write(f"User: {test['USER_NAME'].iloc[0]}")
        except:
            st.error("❌ Snowflake connection failed")
    
    with col2:
        st.markdown("### LLM Provider")
        if llm.provider:
            st.success(f"✅ Provider: {llm.provider.upper()}")
            
            # Test LLM
            if st.button("Test LLM"):
                with st.spinner("Testing..."):
                    response = llm.complete('Respond with: {"status": "ok", "message": "LLM working"}')
                    if response:
                        st.success(f"✅ LLM Response: {response}")
                    else:
                        st.error("❌ LLM not responding")
        else:
            st.error("❌ No LLM configured")
    
    st.markdown("---")
    st.subheader("📊 Throughput Estimates")
    
    throughput_data = {
        "Provider": ["Groq (Free)", "Groq (Paid)", "OpenAI GPT-4o-mini", "OpenAI GPT-4o", "Ollama (Local)"],
        "Candidates/Minute": ["~10-15", "~50-100", "~30-50", "~20-30", "~3-5"],
        "Cost per 100 Screenings": ["$0", "$0.05", "$0.50", "$5.00", "$0"],
        "Max Parallel": [10, 100, 50, 50, 5]
    }
    st.table(pd.DataFrame(throughput_data))