"""
Centralized constants for the entire application.
Includes HTTP status codes, error/success messages, default values,
and prompt templates.
"""

from http import HTTPStatus

# ----------------------------------------------------------------------
# HTTP Status Codes (using Python's http.HTTPStatus for clarity)
# ----------------------------------------------------------------------
STATUS_OK = HTTPStatus.OK
STATUS_CREATED = HTTPStatus.CREATED
STATUS_BAD_REQUEST = HTTPStatus.BAD_REQUEST
STATUS_UNAUTHORIZED = HTTPStatus.UNAUTHORIZED
STATUS_FORBIDDEN = HTTPStatus.FORBIDDEN
STATUS_NOT_FOUND = HTTPStatus.NOT_FOUND
STATUS_INTERNAL_SERVER_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR

# ----------------------------------------------------------------------
# Error Messages
# ----------------------------------------------------------------------
ERR_SESSION_NOT_FOUND = "Session not found or no messages"
ERR_INTERNAL_SERVER = "An internal server error occurred"
ERR_RESUME_NOT_LINKED = "Error: No resume linked to this session."
ERR_SYSTEM_ERROR = "System error. Please try again."
ERR_CHAT_PROCESSING_FAILED = "Failed to process chat message"

# ----------------------------------------------------------------------
# Success Messages
# ----------------------------------------------------------------------
MSG_CHAT_CREATED = "Chat session created successfully"
MSG_MESSAGE_SENT = "Message sent successfully"
MSG_HISTORY_RETRIEVED = "Chat history retrieved successfully"
MSG_SESSION_STARTED = "Chat session started successfully"

# ----------------------------------------------------------------------
# Default / Magic Numbers
# ----------------------------------------------------------------------
DEFAULT_CHAT_HISTORY_LIMIT = 20          # used in controller get_history
DEFAULT_RAG_HISTORY_LIMIT = 7            # used in repository get_session_history
RESUME_COLLECTION_PREFIX = "res_"        # prefix for Qdrant collection names

# ----------------------------------------------------------------------
# Prompt Templates (moved from chat_prompts.py)
# ----------------------------------------------------------------------
REWRITE_QUERY_PROMPT = """
Given the conversation history and a follow-up question, rewrite the follow-up question 
to be a standalone search query that can be used to retrieve information from a resume.

Rules:
1. Do not answer the question. Just rewrite it.
2. If the question is already clear, return it as is.
3. Replace pronouns (he, she, they, it) with "the candidate" or "the resume".
4. Keep the query concise.

History:
{history}

Follow-up Question: {query}
Standalone Query:"""

# ----------------------------------------------------------------------
# Qdrant / Vector Store
# ----------------------------------------------------------------------
QDRANT_LOCAL_PATH = "./qdrant_storage"
QDRANT_EMBEDDING_TEST_TEXT = "test"
VECTOR_DISTANCE_METRIC = "COSINE"

# ----------------------------------------------------------------------
# Interview Module
# ----------------------------------------------------------------------
INTERVIEW_CONTEXT_LENGTH_LIMIT = 4000          # characters of masked text to send
INTERVIEW_MAX_QUESTIONS = 5                    # number of questions before completion
INTERVIEW_FALLBACK_SCORE = 5                   # if score parsing fails
INTERVIEW_SCORE_REGEX_PATTERN = r"Score:\s*(\d+)/10"
INTERVIEW_TIP_REGEX_PATTERN = r"Tip:\s*(.*)" # to extract tip

ERR_NO_RESUME_FOR_SESSION = "No resume found for this session"
ERR_INVALID_SESSION = "Invalid session"
MSG_INTERVIEW_COMPLETED = "Interview completed"

# ----------------------------------------------------------------------
# Redis Defaults (can also stay in config, but moved for consistency)
# ----------------------------------------------------------------------
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_PII_TTL = 7200                        # 2 hours

# ----------------------------------------------------------------------
# Model Defaults
# ----------------------------------------------------------------------
DEFAULT_MODEL_NAME = "gemini-2.5-flash-lite"

# ----------------------------------------------------------------------
# Interview Prompts
# ----------------------------------------------------------------------
INTERVIEW_QUESTION_PROMPT = """
You are a strict technical interviewer conducting a structured interview.

Candidate Resume:
{context}

Task:
Ask ONE technical interview question. 

Rules:
- Choose a topic from this priority order: Skills/Tech Stack → Work Experience → Projects → Problem Solving → System Design
- Ask about topic: {topic}
- Be specific, not generic
- Prefer real-world scenarios
- Return ONLY the question, no explanation
"""


NEXT_QUESTION_PROMPT = """
You are a strict technical interviewer conducting a structured interview.

Candidate Resume:
{context}

Topics already covered: {covered_topics}
Next topic to cover: {next_topic}

Previous Q&A:
{history}

Task:
Ask ONE new technical question specifically about: {next_topic}

Rules:
- Do NOT repeat any topic from: {covered_topics}
- Be specific to the candidate's resume and the given topic
- Return ONLY the question, no explanation
"""

# Add this new constant
INTERVIEW_TOPICS = [
    "Core Skills & Technical Expertise",
    "Work Experience & Responsibilities",
    "Key Achievements & Projects",
    "Problem Solving & Decision Making",
    "Communication & Team Collaboration",
]


EVALUATION_PROMPT = """
You are a strict technical interviewer.
Question: {question}
Candidate Answer: {answer}

Evaluate the answer. Give a score, feedback, and a short 1.5 to 2-line tip on how to improve this specific answer.

Return STRICT format:
Score: X/10
Feedback: <2 lines feedback>
Tip: <1.5-2 lines actionable tip to improve this answer>
"""
FINAL_VERDICT_PROMPT = """
You are an expert technical recruiter. Based on the interview history provided, generate a final evaluation in strict JSON format.

Rules:
- Be concise, structured, and direct.
- Do NOT write long paragraphs.
- Use bullet points only.
- Speak directly to the candidate.
- Start with one-line overall performance summary.
- Keep tone professional but strict.
- Max 2 bullet points per section
- Each bullet max 1 line

Format EXACTLY like this:

Overall, <1-line performance summary>

🔹 Score
<score> / 50

🔹 Strengths
- ...
- ...

🔹 Weaknesses
- ...
- ...

🔹 How to Improve
- ...
- ...

🔹 Answering Strategy Tip
- ...

Input:
{history}
"""
# FINAL_VERDICT_PROMPT = """
# The interview is over. Based on the conversation history below, provide a final verdict.
# Summarize strengths, weaknesses, and overall preparation advice.

# History:
# {history}

# Format:
# Final Report: <Detailed summary and improvement plan>
# """

# ----------------------------------------------------------------------
# Coaching Module Prompts
# ----------------------------------------------------------------------
COACHING_SYSTEM_PROMPT = """
You are an empathetic yet professional AI Career Coach. 
Your goal is to help the candidate improve their interview performance by reviewing their previous answers.

Rules:
1. Tone: Encouraging, constructive, and highly technical.
2. Context: You have access to the candidate's resume and their performance in a recent mock interview.
3. Task: When a user asks "How did I do?" or "How to improve?", use the interview history and tips provided during the session to guide them.
4. Focus: Help them refine their technical explanations and communication style.
"""

COACHING_INITIAL_MESSAGE_PROMPT = """
Based on the candidate's recent interview for the name {name}, 
provide a warm, 2-line greeting as a coach and ask which specific topic 
or question they would like to practice or improve upon today.
"""

# New strict prompt template for coaching answers
COACHING_STRICT_PROMPT_TEMPLATE = """
CRITICAL RULES (MUST FOLLOW - FAILURE MAKES RESPONSE INVALID):

1. You are STRICTLY an Interview Coach, NOT a Resume Reviewer.
2. You MUST base your answer PRIMARILY on the INTERVIEW PERFORMANCE REPORT below.
3. If the user asks about weaknesses, strengths, score, or improvement:
   → You MUST extract the answer directly from the PERFORMANCE REPORT.
4. You are FORBIDDEN from criticizing resume structure, experience length, formatting, or masked PII tokens like <PERSON_1>.
5. The Resume section can ONLY be used to provide specific contextual examples, NOT for evaluation.
6. If your answer does NOT align with the report, it is WRONG.

------------------------
INTERVIEW PERFORMANCE REPORT (HIGHEST PRIORITY - USE THIS FIRST):
{verdict_section}

------------------------
SUPPORTING CONTEXT (Resume - use ONLY for examples, NOT for evaluation):
{resume_text}

------------------------
USER QUESTION: {user_message}

SPECIFIC INSTRUCTION: {instruction}

OUTPUT FORMAT (STRICT):
- Maximum 3 bullet points.
- Each bullet point exactly ONE line.
- No paragraphs, no introductions, no conclusions.
- Use plain bullet points starting with "- ".

YOUR RESPONSE (ONLY BULLETS):
"""
# ----------------------------------------------------------------------
# Resume Processing
# ----------------------------------------------------------------------
TEMP_UPLOAD_DIR = "temp"
CHUNK_SIZE = 700
CHUNK_OVERLAP = 50
DEFAULT_COLLECTION_PREFIX = "res_"

# ----------------------------------------------------------------------
# RAG / Retrieval
# ----------------------------------------------------------------------
BM25_K = 10
DENSE_K = 10
ENSEMBLE_WEIGHTS = [0.4, 0.6]      # [BM25 weight, Dense weight]
SIMILARITY_SEARCH_K = 25            # initial dense retrieval
MAX_COMBINED_DOCS = 20              # after deduplication
TOP_K_AFTER_RERANK = 5
FALLBACK_RESPONSE = "No relevant information found."
RERANK_FALLBACK_RESPONSE = "I'm sorry, I couldn't find relevant information in the resume."
MISSING_INFO_RESPONSE = "Information not provided in the resume."

# ----------------------------------------------------------------------
# RAG Prompt Template
# ----------------------------------------------------------------------
FINAL_RAG_PROMPT_TEMPLATE = """
Role: Senior Technical Recruiter

Task: Answer candidate-related questions based ONLY on the provided context.

Rules:
- If info is missing, say "{missing_info_msg}"
- Be professional and concise.
- Do not hallucinate.

CONTEXT:
{context}

QUESTION: {query}
ANSWER:
"""


# ----------------------------------------------------------------------
# LLM / Model Configuration
# ----------------------------------------------------------------------
DEFAULT_TEMPERATURE = 0.7
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"

# ----------------------------------------------------------------------
# PDF Processing
# ----------------------------------------------------------------------
PDF_NEWLINE_CLEANUP_PATTERN = r"\n{2,}"
PDF_BROKEN_WORD_PATTERN = r"(\w)\n(\w)"
PDF_EXTRA_SPACES_PATTERN = r"\s{2,}"

# ----------------------------------------------------------------------
# PII Vault
# ----------------------------------------------------------------------
PII_MAPPINGS_FILE = "pii_mappings.json"
PII_REDIS_KEY_PREFIX = "pii_vault"

# ----------------------------------------------------------------------
# RAG Helper / Testing (non-production)
# ----------------------------------------------------------------------
RAG_MANUAL_CHUNK_SIZE = 500
RAG_MANUAL_CHUNK_OVERLAP = 100
RAG_MANUAL_SEPARATORS = ["\n\n", "\n", ".", " "]
RAG_MANUAL_MAX_DOCS_BEFORE_RERANK = 20
RAG_MANUAL_QUERY_GENERATION_COUNT = 3

# ----------------------------------------------------------------------
# Rephrasing Prompt (already in constants? Let's ensure it's present)
# ----------------------------------------------------------------------
REPHRASING_PROMPT_TEMPLATE = """
Contextual Query Rewriter:
You are an AI assistant that re-writes user questions to be search-ready. 
Given the conversation history and the latest user message, your goal is to 
create a standalone query that captures the full intent without needing the history.

Rules:
1. If the user refers to "him", "her", "they", or "this candidate", replace it with "the candidate" or "the resume".
2. If the user asks a follow-up like "And tools?", rewrite it as "What tools are mentioned in the candidate's resume?".
3. Do NOT answer the question. Only return the rewritten query.
4. If no history is provided, return the original query as is.

Conversation History:
{history}

User's Latest Message: {query}

Rewritten Standalone Query:"""

# ----------------------------------------------------------------------
# RAG Manual Prompt Template (for testing)
# ----------------------------------------------------------------------
RAG_MANUAL_PROMPT_TEMPLATE = """
You are an Expert HR Professional and Recruiter evaluating a candidate's resume.

RULES FOR ANSWERING:
1. Grounding: Answer STRICTLY based on the provided CONTEXT.
2. No Hallucination: If the user asks for tools, software, or technologies, ONLY list explicit proper nouns (e.g., "Docker", "Microsoft Excel", "Salesforce"). 
3. No Inference from Verbs: Do NOT infer generic tool categories (like "Documentation Tools" or "Presentation Tools") just because the candidate "documented" or "presented" something.
4. Fallback: If the exact information is not explicitly mentioned, simply state "Based on the context, this information is not explicitly mentioned."

CONTEXT:
{context}

QUESTION:
{query}

ANSWER:
"""

# ----------------------------------------------------------------------
# Section Parser
# ----------------------------------------------------------------------
KNOWN_RESUME_SECTIONS = [
    "Technical Skills",
    "Skills",
    "Work Experience",
    "Experience",
    "Projects",
    "Education",
    "Certifications",
    "Summary",
    "Profile"
]
MIN_SECTION_COUNT_FOR_VALID = 2
DUPLICATE_SECTION_THRESHOLD_RATIO = 0.5   # if unique titles < half of total sections, fallback
LLM_PARSE_TEXT_LIMIT = 3000               # characters sent to LLM for section detection
SECTION_PARSE_REGEX_PATTERN = r"Section:\s*(.*?)\nContent:\s*(.*?)(?=Section:|\Z)"

# ----------------------------------------------------------------------
# Main App
# ----------------------------------------------------------------------
APP_TITLE = "Interview Bot AI API"
APP_DESCRIPTION = "Enterprise RAG Pipeline for Resume Analysis and Interviewing"
ROOT_MESSAGE = "✅ API is up and running. Ready for uploads and chat!"