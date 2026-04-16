# backend/app/features/coaching/coaching_service.py

import json
import re
from sqlalchemy.orm import Session
from backend.app.shared.llm.client import get_llm
from backend.app.features.chat.chat_models import ChatSession, ChatMessage
from backend.app.core.logger import get_logger
from backend.app.constants import COACHING_STRICT_PROMPT_TEMPLATE
from backend.app.rag.pipeline import RAGPipeline

logger = get_logger(__name__)


class CoachingService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm()
        self.rag = RAGPipeline()

    def start_coaching_session(self, interview_session_id: str):
        """Create a new coaching session from a completed interview."""
        old_session = self.db.query(ChatSession).filter(ChatSession.id == interview_session_id).first()
        if not old_session:
            return {"error": "Interview session not found"}

        new_session = ChatSession(
            resume_id=old_session.resume_id,
            is_active=True,
            title=f"Coaching: {old_session.title or 'Session'}",
            session_type="coaching"
        )
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)

        welcome_text = "Hi! I've reviewed your interview verdict. I'm ready to help you improve. What should we focus on?"

        ai_msg = ChatMessage(session_id=new_session.id, role="assistant", content=welcome_text)
        self.db.add(ai_msg)
        self.db.commit()

        return {"coaching_session_id": new_session.id, "welcome_message": welcome_text}

    def _normalize_text(self, text: str) -> str:
        text = re.sub(r'^[-*]\s*', '', text)
        text = text.lower()
        text = re.sub(r'[^a-z0-9 ]', '', text)
        return text.strip()

    def _clean_response(self, text: str) -> str:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        unique = []
        seen = set()
        for line in lines:
            norm_key = self._normalize_text(line)
            key = norm_key if norm_key else line
            if key not in seen:
                seen.add(key)
                unique.append(line)
        return "\n".join(unique[:3])

    def _detect_intent(self, message: str) -> str:
        """Enhanced intent detection with more granular categories."""
        msg = message.lower()

        # Example/Sample Answer
        if any(w in msg for w in ["example", "sample answer", "how should i answer", "give me an answer"]):
            return "example"

        # Skills extraction
        if any(w in msg for w in ["skill", "skills"]):
            return "skills"

        # Strategy/Framework
        if any(w in msg for w in ["strategy", "approach", "framework"]):
            return "strategy"

        # Improvement
        if any(w in msg for w in ["improve", "better", "fix", "how to", "explain how", "guide"]):
            return "improvement"

        # Weakness
        if any(w in msg for w in ["weak", "lack", "bad", "negative"]):
            return "weakness"

        # Strength
        if any(w in msg for w in ["strength", "good", "best", "positive"]):
            return "strength"

        # Score
        if "score" in msg:
            return "score"

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
        weaknesses = list(set(sections.get("weaknesses", [])))
        strengths = list(set(sections.get("strengths", [])))
        if strengths:
            lines.append("STRENGTHS FROM REPORT:")
            for s in strengths:
                lines.append(f"- {s}")
        if weaknesses:
            lines.append("WEAKNESSES FROM REPORT:")
            for w in weaknesses:
                lines.append(f"- {w}")
        return "\n".join(lines)

    def get_coaching_answer(self, session_id: str, user_message: str):
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return "Session not found."

        # Conversation history (last 4 messages)
        history_msgs = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(4).all()

        formatted_history = []
        for i, m in enumerate(reversed(history_msgs)):
            content = m.content if i >= 2 else f"{m.content[:100]}..."
            formatted_history.append(f"- {m.role.upper()}: {content}")
        history_text = "\n".join(formatted_history)

        # Enhanced intent detection
        intent = self._detect_intent(user_message)

        # --- CONTEXT ROUTING (Intelligent source selection) ---
        use_verdict = False
        use_rag = False

        if intent == "skills":
            use_verdict = False
            use_rag = True
        elif intent == "example":
            use_verdict = True
            use_rag = True
        elif intent == "improvement":
            use_verdict = True
            use_rag = True
        elif intent == "strategy":
            use_verdict = True
            use_rag = False
        else:  # weakness, strength, score, general
            use_verdict = True
            use_rag = False

        # Prepare RAG context if needed
        rag_context = "NOT NEEDED"
        if use_rag and session.resume and session.resume.chunks_json:
            chunks = session.resume.chunks_json
            relevant_chunks = self.rag.retrieve_only(
                query=user_message,
                chunks=chunks,
                collection_name=f"res_{session.resume_id}"
            )
            rag_context = "\n".join(relevant_chunks)[:800]

        # Prepare verdict context if needed
        verdict_section_text = "IGNORE THIS SECTION"
        if use_verdict:
            last_interview = self.db.query(ChatSession).filter(
                ChatSession.resume_id == session.resume_id,
                ChatSession.final_verdict.isnot(None)
            ).order_by(ChatSession.created_at.desc()).first()
            if last_interview:
                verdict_sections = self._extract_verdict_sections(last_interview.final_verdict)
                verdict_section_text = self._build_verdict_section_text(verdict_sections, intent)
            else:
                return "Please complete an interview first."

        # --- INTELLIGENT MODE INSTRUCTIONS ---
        if intent == "example":
            mode_instruction = """
            INTERVIEW ANSWER MODE:

            - Generate a REAL answer the candidate can speak in an interview.
            - Use first-person ("I would...", "In my experience...").
            - Include structured steps.
            - Include one concrete, realistic example.
            - Be concise but natural.

            Format:
            - Max 2 bullets.
            - Each bullet should be a complete, speakable answer.
            """
        elif intent == "skills":
            mode_instruction = """
            SKILL EXTRACTION MODE:

            - Extract ONLY skills explicitly mentioned in the resume.
            - Do NOT include weaknesses, evaluation, or anything from the interview report.
            - Do NOT infer skills not present.
            - Do NOT add commentary.

            Output:
            - Bullet points only (max 5).
            """
        elif intent == "strategy":
            mode_instruction = """
            STRATEGY FRAMEWORK MODE:

            - Provide a structured framework for answering this type of question.
            - Give steps (e.g., Step 1, Step 2).
            - Focus on approach, not content.
            - Based on the interview report's identified gaps.

            Output:
            - Bullet points (max 3).
            """
        elif intent == "improvement":
            mode_instruction = """
            INTERVIEW ADVISOR MODE:

            - Provide technical advice based on the resume context and interview report.
            - Suggest specific methods or tools the candidate can use to bolster their answer.
            - DO NOT provide a script. Provide technical guidance.
            - Constraint: ONLY use technologies present in the provided context.
            """
        else:  # weakness, strength, score, general
            mode_instruction = "EXTRACTION MODE: Answer based directly on the interview report summary. Be concise."

        # Build the final prompt
        prompt = COACHING_STRICT_PROMPT_TEMPLATE.format(
            verdict_section=verdict_section_text,
            resume_text=rag_context,
            user_message=user_message,
            instruction=f"{mode_instruction}\n[HISTORY]:\n{history_text}"
        )

        raw_response = self.llm.invoke(prompt).content.strip().replace("```", "").strip()
        final_response = self._clean_response(raw_response)

        # --- HARD BACKEND FILTER for skills intent ---
        if intent == "skills":
            filtered_lines = []
            for line in final_response.split("\n"):
                lower_line = line.lower()
                if not any(w in lower_line for w in ["weak", "lack", "improve", "fail", "missing"]):
                    filtered_lines.append(line)
            final_response = "\n".join(filtered_lines) if filtered_lines else final_response

        # Save to DB
        self.db.add_all([
            ChatMessage(session_id=session_id, role="user", content=user_message),
            ChatMessage(session_id=session_id, role="assistant", content=final_response)
        ])
        self.db.commit()

        return final_response