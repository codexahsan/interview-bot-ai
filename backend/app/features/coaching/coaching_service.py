# backend/app/features/coaching/coaching_service.py

import json
from sqlalchemy.orm import Session
from backend.app.shared.llm.client import get_llm
from backend.app.features.chat.chat_models import ChatSession, ChatMessage
from backend.app.core.logger import get_logger
from backend.app.constants import COACHING_STRICT_PROMPT_TEMPLATE
from backend.app.rag.pipeline import RAGPipeline
import re

logger = get_logger(__name__)


class CoachingService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm()
        self.rag = RAGPipeline()

    def _normalize_text(self, text: str) -> str:
        """Removes bullet points, special chars and extra spaces."""
        text = re.sub(r'^[-*]\s*', '', text) 
        text = text.lower()
        text = re.sub(r'[^a-z0-9 ]', '', text)
        return text.strip()

    def _clean_response(self, text: str) -> str:
        """Enforces unique bullets by comparing normalized keys."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        unique = []
        seen = set()

        for l in lines:
            norm_key = self._normalize_text(l)
            
            # Agar line mein kuch technical bacha hi nahi (sirf symbols), 
            # to original line use karein as key, warna normalized key.
            key = norm_key if norm_key else l

            # CRITICAL: Yeh IF block for loop ke ANDAR hona chahiye
            if key not in seen:
                seen.add(key)
                unique.append(l)

        # 2. Return result ONLY AFTER loop finishes
        return "\n".join(unique[:3])

    def _detect_intent(self, message: str, last_bot_msg: str = "") -> str:
        """
        Improved Intent Detection: Separating 'extraction' from 'transformation'.
        """
        msg = message.lower()

        # Mode 2: Transformation (Improvement/Actionable advice) - HIGH PRIORITY
        if any(word in msg for word in ["improve", "better", "how to", "fix", "explain how", "guide"]):
            return "improvement"
        
        # Mode 1: Extraction (Safe/Direct info)
        elif any(word in msg for word in ["weak", "lack", "bad", "negative"]):
            return "weakness"
        elif any(word in msg for word in ["strength", "good", "best", "positive"]):
            return "strength"
        elif "score" in msg:
            return "score"
        else:
            return "general"

    def _extract_verdict_sections(self, verdict_json_str: str) -> dict:
        try:
            verdict_data = json.loads(verdict_json_str)
        except:
            return {"weaknesses": [], "strengths": [], "score": None, "evaluation": ""}

        return {
            "weaknesses": verdict_data.get("weaknesses", []),
            "strengths": verdict_data.get("strengths", []),
            "score": verdict_data.get("score"),
            "evaluation": verdict_data.get("evaluation", "")
        }

    def _build_verdict_section_text(self, sections: dict, intent: str) -> str:
        lines = []
        if sections.get("evaluation"):
            lines.append(f"Overall Performance: {sections['evaluation']}")
        
        # We provide all context to the LLM, but the instruction will tell it what to focus on
        weaknesses = list(set(sections.get("weaknesses", [])))
        strengths = list(set(sections.get("strengths", [])))

        if strengths:
            lines.append("STRENGTHS FROM REPORT:")
            for s in strengths: lines.append(f"- {s}")
        
        if weaknesses:
            lines.append("WEAKNESSES FROM REPORT:")
            for w in weaknesses: lines.append(f"- {w}")

        return "\n".join(lines)

    def get_coaching_answer(self, session_id: str, user_message: str):
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session: return "Session not found."

        # 1. SMART MEMORY (Last 2 Full, previous 2 Truncated)
        history_msgs = self.db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.desc()).limit(4).all()
        
        formatted_history = []
        for i, m in enumerate(reversed(history_msgs)):
            content = m.content if i >= 2 else f"{m.content[:100]}..."
            formatted_history.append(f"- {m.role.upper()}: {content}")
        history_text = "\n".join(formatted_history)

        # 2. LIGHTWEIGHT RAG (Only for Improvements)
        intent = self._detect_intent(user_message)
        rag_context = "No specific context needed."
        
        if intent == "improvement":
            chunks = session.resume.chunks_json if session.resume and session.resume.chunks_json else []
            # Fast retrieval: Top 2 chunks only to save tokens
            relevant_chunks = self.rag.retrieve_only(query=user_message, chunks=chunks, collection_name=f"res_{session.resume_id}")
            rag_context = "\n".join(relevant_chunks[:2])[:800]

        # 3. VERDICT FETCHING & HALLUCINATION GUARD
        last_interview = self.db.query(ChatSession).filter(ChatSession.resume_id == session.resume_id, ChatSession.final_verdict.isnot(None)).order_by(ChatSession.created_at.desc()).first()
        if not last_interview: return "Please complete an interview first."

        verdict_sections = self._extract_verdict_sections(last_interview.final_verdict)

        # 4. REFINED INSTRUCTIONS (No "Say this" imposition)
        if intent == "improvement":
            mode_instruction = """
            INTERVIEW ADVISOR MODE:
            - Provide technical advice based ONLY on the resume context and interview report.
            - Suggest specific methods or tools (e.g., JWT, Bcrypt) the candidate can use to bolster their answer.
            - DO NOT provide a script. Provide technical guidance.
            - Constraint: ONLY use technologies present in the provided context.
            """
        else:
            mode_instruction = "EXTRACTION MODE: Answer based directly on the interview report summary."

        prompt = COACHING_STRICT_PROMPT_TEMPLATE.format(
            verdict_section=self._build_verdict_section_text(verdict_sections, intent),
            resume_text=rag_context,
            user_message=user_message,
            instruction=f"{mode_instruction}\n[HISTORY]:\n{history_text}"
        )

        raw_response = self.llm.invoke(prompt).content.strip().replace("```", "").strip()
        final_response = self._clean_response(raw_response)

        # 5. SAVE & RETURN
        self.db.add_all([
            ChatMessage(session_id=session_id, role="user", content=user_message),
            ChatMessage(session_id=session_id, role="assistant", content=final_response)
        ])
        self.db.commit()
        return final_response