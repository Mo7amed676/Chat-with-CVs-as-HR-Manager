# ⚡ HR AI Assistant

## 📋 Project Overview
**HR AI Assistant** is a Streamlit-based web application that uses Google Generative AI (Gemini) and LangChain to intelligently process CV PDFs and answer questions about candidates through natural language queries.

## ✨ Key Features

### 📤 CV Processing
- **Multi-file PDF Upload**: Process multiple CV files simultaneously
- **Intelligent Metadata Extraction**: 
  - Extracts: Name, Email, Phone, Job Title, Experience Years, Skills
  - Dual-approach: LLM extraction with regex fallback for guaranteed results
- **Vector Database**: Creates searchable embeddings using ChromaDB
- **Pipeline Logging**: Real-time processing logs with visual feedback

### 💬 AI-Powered Q&A
- **Smart Question Answering**: Uses RAG (Retrieval-Augmented Generation) with similarity search
- **Preset Quick Questions**: 
  - "Who has Python experience?"
  - "Show candidates with SQL skills"
  - "Who is suitable for AI Engineer role?"
  - "List all names and titles"
- **Custom Questions**: Ask anything about candidates
- **Conversation History**: Maintains chat message history

### 📊 Data Management
- **Candidates Dashboard**: View all extracted candidate data
- **CSV Export**: Download candidate data as CSV file
- **Real-time Metrics**: 
  - Total candidates count
  - Candidates with email contact
  - Candidates with phone contact
- **Two-Tab Interface**: Separate "Ask Questions" and "Candidates Data" tabs

### 🐛 Debug Mode
- Toggle debug mode in sidebar
- View LLM extraction responses
- See processing pipeline details

## 🏗️ Architecture

```
app.py (Frontend)
    ↓
Streamlit UI Components
    ├── Sidebar: File upload, debug mode, pipeline log
    ├── Tab 1: Chat interface with Q&A
    └── Tab 2: Data table and CSV export
    
utils.py (Backend)
    ├── process_cvs_final() → PDF loading + metadata extraction
    ├── extract_metadata_with_fallback() → LLM + Regex parsing
    ├── answer_question() → Vector search + LLM response
    └── get_candidates_df() → Data formatting
    
Google Generative AI
    ├── Gemini 2.5-Flash (LLM for Q&A)
    └── Embedding-001 (Vector embeddings)
    
Data Storage
    ├── ChromaDB (Vector store)
    └── Session State (Streamlit memory)
```

## 📁 Project Structure

```
Chat-with-CVs-as-HR-Manager/
├── app.py              # Main Streamlit application (186 lines)
├── utils.py            # Backend utilities & LLM logic (382 lines)
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (GOOGLE_API_KEY)
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## 🛠️ Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/Mo7amed676/Chat-with-CVs-as-HR-Manager.git
cd Chat-with-CVs-as-HR-Manager
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

**Dependencies:**
- `streamlit` - Web UI framework
- `langchain` - LLM orchestration
- `langchain-google-genai` - Google AI integration
- `langchain-community` - Community tools
- `chromadb` - Vector database
- `pypdf` - PDF processing
- `python-dotenv` - Environment management
- `tiktoken` - Token counting
- `pandas` - Data manipulation
- `plotly` - Data visualization

### 3. Configure API Key
Create a `.env` file in the root directory:
```
GOOGLE_API_KEY=your_google_api_key_here
```

Get your API key from: https://makersuite.google.com/app/apikey

### 4. Run Application
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## 🚀 Usage Guide

### Step 1: Upload CVs
1. Click **"📤 Upload CVs"** in the sidebar
2. Select one or multiple PDF files
3. Enable **"🐛 Debug Mode"** to see extraction details (optional)
4. Click **"🔄 Process CVs"** button

### Step 2: Ask Questions
#### Using Quick Questions (Tab 1)
Click any of the preset buttons:
- "Who has Python experience?"
- "Show candidates with SQL skills"
- "Who is suitable for AI Engineer role?"
- "List all names and titles"

#### Using Custom Questions
Type any question in the chat input:
- "Compare candidates based on experience"
- "Who has both Python and SQL?"
- "Best candidate for Data Engineer role?"

### Step 3: View Results
- **Text Answers**: Default response format
- **Table Format**: Automatically shown for queries with "table", "csv", "export", "spreadsheet", "excel"
- **Conversation History**: All Q&A appears in chat window

### Step 4: Export Data (Tab 2)
1. Switch to **"📋 Candidates Data"** tab
2. View formatted candidate table
3. Click **"📥 Download as CSV"** to export
4. Check metrics: Total candidates, contacts with email/phone

## 📚 Core Functions

### `app.py` Functions

| Function | Purpose |
|----------|---------|
| `st.set_page_config()` | Configure page title and layout |
| `st.session_state` | Manage app state (vectorstore, messages, log) |
| `st.file_uploader()` | Handle PDF file uploads |
| `process_cvs_final()` | Process uploaded files (calls utils) |
| `answer_question()` | Generate AI responses (calls utils) |
| `get_candidates_df()` | Format data for display (calls utils) |

### `utils.py` Functions

#### `process_cvs_final(uploaded_files, debug=False)`
Processes CV files and creates vector database.

**Input:**
- `uploaded_files`: List of PDF file objects
- `debug`: Boolean to enable debug output

**Output:**
- `vectorstore`: ChromaDB vector store for similarity search
- `candidates`: List of candidate metadata dictionaries
- `log`: Processing log messages

**Process:**
```
PDF Load → Text Extraction → Metadata Parsing → Chunking → Embedding → Vector Store
```

#### `extract_metadata_with_fallback(cv_text, filename, debug=False)`
Extracts candidate info with dual approach.

**Strategy:**
1. **Try LLM First**: Uses Gemini to parse CV format
2. **Fallback to Regex**: If LLM fails, uses regex patterns

**Extracted Fields:**
- `name`: Candidate full name
- `phone`: Phone number (Egyptian formats supported)
- `email`: Email address
- `current_title`: Job title
- `experience_years`: Years of experience
- `skills`: List of detected skills

#### `answer_question(vectorstore, question, candidates)`
Generates answers using RAG and LLM.

**Process:**
1. Build candidates summary
2. Search vector database for relevant CV chunks
3. Format context from results
4. Call Gemini with smart prompt
5. Return formatted answer

**Smart Features:**
- Detects specific candidate mentions
- Increases search results (k=12) for comparison queries
- Uses markdown tables for comparisons
- Filters results by candidate name if mentioned

#### `get_candidates_df(candidates)`
Formats candidate data for table display.

**Returns:** Pandas DataFrame with columns:
- name, phone, email, current_title, experience_years, filename

#### `extract_candidates_for_query(question, candidates)`
Filters candidates based on skill/title matching.

**Scoring:**
- Skills match: +3 points
- Title match: +2 points
- Experience ≥3 years: +1 point

Returns top 10 matching candidates.

## ⚙️ Configuration

### Models
- **LLM Model**: `gemini-2.5-flash` (fast, latest)
- **Embedding Model**: `models/gemini-embedding-001`

### Prompts

**META_PROMPT** - CV metadata extraction format:
```
NAME: [clean name only]
PHONE: [number or N/A]
EMAIL: [email or N/A]
TITLE: [job title or N/A]
YEARS: [number or N/A]
SKILLS: [skill1, skill2, skill3]
```

**QA_PROMPT** - Smart question answering:
- Detects "list all" → shows candidate summary
- Detects "compare" → generates comparison table
- Specific candidate name → focuses on that CV
- Default → general Q&A response

### Text Processing
- **Chunk Size**: 1000 characters
- **Chunk Overlap**: 150 characters
- **Similarity Search k**: 6 (default), 12 (comparisons)
- **Max Skills**: 5 per candidate
- **Regex Skills**: Python, Java, JavaScript, SQL, ML, AI, React, Docker, AWS, Azure, Git, TensorFlow, PyTorch

## 🔍 Regex Patterns

### Phone Detection (Egyptian formats)
- `+201XXXXXXXXX` (international)
- `00201XXXXXXXXX` (international alt)
- `01XXXXXXXXX` (national)
- `01XXXX XXXX` (formatted)

### Email Detection
- Standard email pattern: `user@domain.com`

### Title Extraction
- Position/Title/Role patterns
- "Working as" / "Currently" patterns
- Role + Job title patterns (Developer, Engineer, Manager, etc.)

### Skills Detection
Pre-defined keyword list automatically matched in CV text.

## 🎯 Example Queries

| Query | Expected Behavior |
|-------|-------------------|
| "Who has Python experience?" | Lists candidates with Python skill |
| "Compare candidates" | Shows comparison table |
| "Show table" | Displays candidate data table |
| "Best candidate for AI Engineer?" | Analyzes CVs and recommends best fit |
| "Who is john?" | Focuses on John's CV content |
| "List all names and titles" | Shows summary of all candidates |

## 🐛 Troubleshooting

### Issue: "⚠️ System not ready"
**Solution**: Process CVs first before asking questions

### Issue: No candidates extracted
**Solution**: 
- Check PDF quality and format
- Enable debug mode to see extraction details
- Ensure PDFs contain readable text

### Issue: Slow responses
**Solution**:
- Reduces chunk overlap for faster processing
- Check API rate limits

### Issue: Wrong metadata extraction
**Solution**:
- Enable debug mode to see LLM response
- Regex fallback will still provide basic extraction
- Ensure CV follows standard format

## 📝 Notes

- The app uses **Streamlit session state** to persist data during session
- **Vector embeddings** enable semantic search across CV content
- **Fallback regex extraction** guarantees data even if LLM fails
- **Dual-prompt approach**: Separate prompts for extraction and Q&A
- Supports **Egyptian phone formats** by default
- All responses are in **ENGLISH only**

## 🔐 Security Notes

- Store `GOOGLE_API_KEY` in `.env` file only (never commit)
- PDFs are processed in memory and temp files are cleaned up
- No permanent storage of CV content on server
- Session data is cleared per browser session

## 📞 Support

For issues or questions, check:
1. Debug mode output (enabled in sidebar)
2. Pipeline logs in sidebar
3. Check if PDF files are readable
4. Verify Google API key is valid

---

**Built with ❤️ using LangChain, Streamlit & Google Gemini**
<ins>Mohamed Mahmoud</ins>
