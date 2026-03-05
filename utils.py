import os
import re
import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure  # ✅ أضف السطر ده

from typing import List, Optional, Dict, Any, Tuple

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field
import streamlit as st

from typing import List, Dict, Any, Optional
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
import streamlit as st

# Load Environment Variables
load_dotenv()

# --- Configuration ---
MODEL_NAME = "gemini-2.5-flash"  # أسرع وأحدث موديل مناسب للمهام دي
EMBEDDING_MODEL = "models/gemini-embedding-001"

META_PROMPT = """Extract from this CV. Respond in EXACT format below:

NAME: [clean name only]
PHONE: [number or N/A]
EMAIL: [email or N/A]
TITLE: [job title or N/A]
YEARS: [number or N/A]
SKILLS: [skill1, skill2, skill3]

CV:
{cv_text}

Response:"""
QA_PROMPT = """You are an expert HR Assistant. Answer in ENGLISH only.

IMPORTANT INSTRUCTIONS:
1. If user asks to "list all", "show everyone", "count candidates" → Use CANDIDATES SUMMARY to list EVERY candidate.
2. If user asks about a SPECIFIC person → Focus ONLY on {target_candidate} in CV CONTENT.
3. ⭐ If user asks for "comparison", "compare", "who is better", "most fit", "best candidate" → 
   - Analyze the CV CONTENT carefully
   - Compare candidates based on the job requirements mentioned
   - Generate a MARKDOWN TABLE comparing: Name, Key Skills, Experience, Why They Fit
   - Recommend the best candidate with reasoning
4. If user just says "table" or "csv" without comparison context → Use CANDIDATES SUMMARY to show basic info.

CANDIDATES SUMMARY (Use for "list all" or basic "table" requests):
{candidates_summary}

CV CONTENT (Use for comparisons, skills, specific questions):
{cv_content}

Question: {question}

Answer (be professional, follow instructions above, use markdown tables for comparisons):"""
# ==========================================
# REGEX FALLBACK (Guaranteed Extraction)
# ==========================================

def regex_extract_fallback(text: str, filename: str) -> Dict[str, Any]:
    """Fallback regex extraction when LLM fails"""
    data = {
        "filename": filename,
        "name": os.path.splitext(filename)[0].replace('-', ' ').replace('_', ' '),
        "phone": "N/A",
        "email": "N/A",
        "current_title": "N/A",
        "experience_years": "N/A",
        "skills": []
    }
    
    # Email regex
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match:
        data["email"] = email_match.group().strip()
    
    # Phone regex (Egyptian)
    phone_patterns = [
        r'(\+201[0-9]{9})', r'(00201[0-9]{9})', r'(01[0-9]{9})',
        r'(01\d\s?\d{4}\s?\d{4})', r'(\+20\s?1[0-9]\s?[0-9]{8})'
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone = re.sub(r'[^\d+]', '', match.group())
            if len(phone) >= 10:
                data["phone"] = phone
                break
    
    # Name from first line (if looks like name)
    lines = text.split('\n')
    for line in lines[:3]:
        line = line.strip()
        if 10 < len(line) < 50 and re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)+', line):
            clean = re.sub(r'\s*\([^)]*\)', '', line).strip()
            if len(clean) > 5:
                data["name"] = clean
                break
    
    # Title extraction
    title_patterns = [
        r'(?:position|title|role)\s*[:\-]?\s*([A-Za-z\s\.]+?)(?:\n|$)',
        r'(?:working as|currently)\s+(?:a\s+)?([A-Za-z\s\.]+?)(?:\n|at|,|$)',
        r'([A-Za-z]+\s+(Developer|Engineer|Manager|Designer|Analyst))'
    ]
    for pattern in title_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            data["current_title"] = match.group(1).strip()
            break
    
    # Experience years
    exp_match = re.search(r'(\d+)\+?\s*(?:year|years|سنة|عام)', text, re.I)
    if exp_match:
        data["experience_years"] = exp_match.group(1)
    
    # Skills (keyword match)
    skills_kw = ['python','java','javascript','sql','machine learning','ai','react',
                 'docker','aws','azure','git','agile','tensorflow','pytorch']
    found = [s for s in skills_kw if s.lower() in text.lower()]
    data["skills"] = list(set(found))[:5]
    
    return data

# ==========================================
# CORE FUNCTIONS
# ==========================================

def get_model(temp=0.1):
    try:
        return GoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=temp,
            request_timeout=60
        )
    except:
        return None

def get_embeddings():
    try:
        return GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    except:
        return None

def extract_metadata_with_fallback(cv_text: str, filename: str, debug: bool = False) -> Dict[str, Any]:
    """Extract metadata: LLM first, then regex fallback"""
    
    # Try LLM first
    model = get_model(0)
    if model:
        try:
            prompt = META_PROMPT.format(cv_text=cv_text[:3500])
            response = model.invoke(prompt)
            
            if debug:
                st.write(f"🔍 LLM Response for {filename}:")
                st.code(response[:500])
            
            # Parse LLM response (flexible parsing)
            result = {}
            for line in response.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    result[key.strip().upper()] = val.strip()
            
            # Build output
            if result.get('NAME') and result.get('NAME') != '[clean name only]':
                return {
                    "filename": filename,
                    "name": result.get('NAME', os.path.splitext(filename)[0]),
                    "phone": result.get('PHONE', 'N/A'),
                    "email": result.get('EMAIL', 'N/A'),
                    "current_title": result.get('TITLE', 'N/A'),
                    "experience_years": result.get('YEARS', 'N/A'),
                    "skills": [s.strip() for s in result.get('SKILLS', '').split(',') if s.strip()]
                }
        except Exception as e:
            if debug:
                st.warning(f"⚠️ LLM extract failed: {e}")
    
    # Fallback to regex (GUARANTEED to return something)
    if debug:
        st.info(f"🔄 Using regex fallback for {filename}")
    
    return regex_extract_fallback(cv_text, filename)

def process_cvs_final(uploaded_files, debug: bool = False) -> tuple:
    """Process CVs with guaranteed metadata extraction"""
    if not uploaded_files:
        return None, [], []
    
    candidates = []
    all_docs = []
    log = []
    
    log.append(f"📂 Starting: {len(uploaded_files)} files")
    
    for idx, file in enumerate(uploaded_files, 1):
        filename = file.name
        log.append(f"📄 [{idx}/{len(uploaded_files)}] {filename}")
        
        try:
            # Load PDF
            temp_path = f"temp_{filename}"
            with open(temp_path, "wb") as f:
                f.write(file.getbuffer())
            
            loader = PyPDFLoader(temp_path)
            pages = loader.load()
            full_text = " ".join([p.page_content for p in pages])
            log.append(f"   ✅ Text: {len(pages)}p, {len(full_text)} chars")
            
            # Extract metadata (with fallback)
            meta = extract_metadata_with_fallback(full_text, filename, debug)
            candidates.append(meta)
            log.append(f"   ✅ Meta: {meta['name']} | 📧 {meta['email']} | 📱 {meta['phone']}")
            
            # Document-aware chunking
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            chunks = splitter.split_text(full_text)
            
            for i, chunk in enumerate(chunks):
                all_docs.append(Document(
                    page_content=chunk,
                    metadata={
                        "source": filename,
                        "candidate": meta['name'],
                        "phone": meta['phone'],
                        "email": meta['email'],
                        "title": meta['current_title'],
                        "chunk_id": i
                    }
                ))
            
            log.append(f"   ✅ Chunks: {len(chunks)}")
            os.remove(temp_path)
            
        except Exception as e:
            log.append(f"   ❌ Error: {str(e)[:80]}")
            continue
    
    if not all_docs:
        log.append("❌ No documents indexed")
        return None, candidates, log
    
    # Create vectorstore
    log.append("🔢 Embedding...")
    embeddings = get_embeddings()
    if not embeddings:
        log.append("❌ Embeddings failed")
        return None, candidates, log
    
    vectorstore = Chroma.from_documents(documents=all_docs, embedding=embeddings)
    log.append(f"✅ Done: {len(candidates)} CVs, {len(all_docs)} chunks")
    
    return vectorstore, candidates, log
def answer_question(vectorstore, question: str, candidates: List[Dict]) -> str:
    model = get_model(0.2)
    if not model or not vectorstore:
        return "⚠️ System not ready."
    
    try:
        # Build Candidates Summary
        summary_lines = []
        for c in candidates:
            name = c.get('name', 'Unknown')
            phone = c.get('phone', 'N/A')
            email = c.get('email', 'N/A')
            title = c.get('current_title', 'N/A')
            skills = ', '.join(c.get('skills', [])[:3])
            summary_lines.append(f"- {name} | {title} | 📱 {phone} | 📧 {email} | Skills: {skills}")
        
        candidates_summary = "\n".join(summary_lines) if summary_lines else "No candidates data available."
        
        # Check if question mentions specific candidate
        question_lower = question.lower()
        target_candidate = None
        for c in candidates:
            name = c.get('name', '').lower()
            if name and name in question_lower:
                target_candidate = c.get('name')
                break
        
        # Retrieve chunks
        if target_candidate:
            results = vectorstore.similarity_search(question, k=10, filter={"candidate": target_candidate})
        else:
            # ✅ Increase k for comparison questions to get more context
            k_value = 12 if any(w in question_lower for w in ["compare", "comparison", "better", "best", "fit"]) else 6
            results = vectorstore.similarity_search(question, k=k_value)
        
        # Build context
        context_parts = []
        seen = set()
        for doc in results:
            src = doc.metadata.get('source', '')
            if src not in seen:
                seen.add(src)
                candidate = doc.metadata.get('candidate', 'Unknown')
                context_parts.append(f"[{candidate} - {src}]\n{doc.page_content[:700]}")
        
        cv_content = "\n\n".join(context_parts) if context_parts else "No detailed CV content found."
        
        # Call LLM with smart prompt
        prompt = QA_PROMPT.format(
            question=question,
            candidates_summary=candidates_summary,
            cv_content=cv_content,
            target_candidate=target_candidate if target_candidate else "any candidate"
        )
        
        return model.invoke(prompt).strip()
        
    except Exception as e:
        return f"⚠️ Error: {str(e)[:150]}"
    
def get_candidates_df(candidates: List[Dict]) -> pd.DataFrame:
    """Return clean DataFrame for display"""
    if not candidates:
        return pd.DataFrame()
    df = pd.DataFrame(candidates)
    cols = ["name","phone","email","current_title","experience_years","filename"]
    return df[[c for c in cols if c in df.columns]].copy()

# ==========================================
# ✅ NEW: SMART FILTERING FOR TABLE OUTPUT
# ==========================================

def extract_candidates_for_query(question: str, candidates: List[Dict]) -> List[Dict]:
    """
    Filter candidates based on simple keyword matching for table display.
    Used when user asks "Who has X?" to show results as a nice table.
    """
    if not candidates:
        return []
    
    q_lower = question.lower()
    matches = []
    
    for candidate in candidates:
        score = 0
        
        # Check skills match
        skills = [s.lower() for s in candidate.get('skills', [])]
        if any(skill in q_lower for skill in skills):
            score += 3
        
        # Check title match
        title = candidate.get('current_title', '').lower()
        title_keywords = ["engineer", "developer", "ai", "python", "sql", "data", "ml"]
        if any(kw in title for kw in title_keywords) and any(kw in q_lower for kw in title_keywords):
            score += 2
        
        # Check experience if mentioned in query
        exp = candidate.get('experience_years', '0')
        if exp.isdigit() and ("experience" in q_lower or "year" in q_lower):
            if int(exp) >= 3:
                score += 1
        
        # Include candidate if score > 0
        if score > 0:
            matches.append(candidate)
    
    # Sort by number of skills (more skills = more relevant)
    return sorted(matches, key=lambda x: len(x.get('skills', [])), reverse=True)[:10]