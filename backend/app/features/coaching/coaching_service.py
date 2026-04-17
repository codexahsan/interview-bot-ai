# backend/app/features/coaching/coaching_service.py

import json
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from backend.app.shared.llm.client import get_llm, get_embeddings
from backend.app.features.chat.chat_models import ChatSession, ChatMessage
from backend.app.core.logger import get_logger
from backend.app.constants import COACHING_STRICT_PROMPT_TEMPLATE, INTENT_EXAMPLES, EMBEDDING_SIMILARITY_THRESHOLD
from backend.app.rag.pipeline import RAGPipeline

logger = get_logger(__name__)


class IntentClassifier:
    def __init__(self):
        self.embedder = get_embeddings()
        self.intent_examples = INTENT_EXAMPLES
        self.intent_embeddings = {}
        for intent, examples in self.intent_examples.items():
            if examples:
                self.intent_embeddings[intent] = self.embedder.embed_documents(
                    examples, output_dimensionality=768
                )

    def get_intent(self, message: str) -> str:
        if not message or not message.strip():
            return "general"

        msg_lower = message.lower().strip()

        # LAYER 1: Keyword Rules (refinement has high priority)
        if any(w in msg_lower for w in ["name", "email", "phone", "contact", "address", "personal detail"]):
            return "pii"
        if any(w in msg_lower for w in ["skill", "technology", "framework", "language i know"]):
            return "skills"
        if any(w in msg_lower for w in ["experience", "project", "education", "worked", "cv", "resume", "background"]):
            return "resume"
        if any(phrase in msg_lower for phrase in ["strategy", "approach", "framework", "how should i answer", "way to answer", "structure my answer"]):
            return "strategy"
        if any(phrase in msg_lower for phrase in ["example", "sample answer", "model answer", "how would you answer"]):
            return "example"
        if any(phrase in msg_lower for phrase in ["make it simpler", "simpler", "simplify", "shorter", "concise", "make it short", "easy language"]):
            return "refinement"
        if any(phrase in msg_lower for phrase in ["improve", "better", "fix", "stronger", "refine", "polish", "make this better", "improve this", "improve it"]):
            return "improvement"
        if any(w in msg_lower for w in ["weak", "lack", "bad", "poor", "mistake", "wrong"]):
            return "weakness"
        if any(w in msg_lower for w in ["strength", "good", "best", "well done"]):
            return "strength"

        # LAYER 2: Embedding + LLM Fallback
        try:
            msg_embedding = self.embedder.embed_query(message, output_dimensionality=768)
            msg_emb = np.array(msg_embedding).reshape(1, -1)

            best_intent = "general"
            best_score = 0.0

            for intent, emb_list in self.intent_embeddings.items():
                if not emb_list:
                    continue
                emb_matrix = np.array(emb_list)
                sim_scores = cosine_similarity(msg_emb, emb_matrix)[0]
                max_sim = float(np.max(sim_scores))
                if max_sim > best_score:
                    best_score = max_sim
                    best_intent = intent

            if best_score >= EMBEDDING_SIMILARITY_THRESHOLD:
                return best_intent

            return self._llm_intent_fallback(message)
        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            return "general"

    def _llm_intent_fallback(self, message: str) -> str:
        llm = get_llm()
        prompt = f"""Classify the user message into exactly one intent: improvement, refinement, example, strategy, weakness, strength, skills, resume, pii, general.

Message: "{message}"

Reply with only the intent name in lowercase."""
        try:
            response = llm.invoke(prompt).content.strip().lower()
            valid = {"improvement", "refinement", "example", "strategy", "weakness", "strength", "skills", "resume", "pii", "general"}
            return response if response in valid else "general"
        except:
            return "general"


class CoachingService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm()
        self.rag = RAGPipeline()
        self.intent_classifier = IntentClassifier()

        # -------------------------------------------------------------------------
    # Reference Resolver - Now driven by plan (Final Version)
    # -------------------------------------------------------------------------
    def _resolve_reference(self, user_message: str, session_id: str, plan: dict) -> str:
        """Attach previous answer ONLY if the plan says we need reference."""
        if not plan.get("needs_reference", False):
            return user_message

        last_ai_msg = (
            self.db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant"
            )
            .order_by(ChatMessage.created_at.desc())
            .first()
        )

        if not last_ai_msg:
            return user_message

        # Always attach when plan demands it (refinement or improvement)
        return f"""Refine or improve the following previous answer according to the user request.

        PREVIOUS ANSWER TO WORK ON:
        {last_ai_msg.content}

        USER REQUEST: {user_message}"""

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------
    def start_coaching_session(self, interview_session_id: str):
        old_session = self.db.query(ChatSession).filter(ChatSession.id == interview_session_id).first()
        if not old_session:
            return {"error": "Interview session not found"}

        new_session = ChatSession(
            resume_id=old_session.resume_id,
            is_active=True,
            title=f"Coaching: {old_session.title or 'Session'}",
            session_type="coaching",
        )
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)

        welcome_text = "Hi! I've reviewed your interview verdict. I'm ready to help you improve. What should we focus on?"

        ai_msg = ChatMessage(session_id=new_session.id, role="assistant", content=welcome_text)
        self.db.add(ai_msg)
        self.db.commit()

        return {"coaching_session_id": new_session.id, "welcome_message": welcome_text}

    def get_coaching_answer(self, session_id: str, user_message: str):
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return "Session not found."

        intent = self._detect_intent(user_message)

        # Handle fully deterministic cases first
        if intent == "pii":
            return self._handle_pii_deterministic(session, session_id, user_message)

        if intent == "skills":
            from backend.app.shared.utils.skills_extractor import hybrid_extract_skills
            text = session.resume.masked_text if session.resume else ""
            skills_output = hybrid_extract_skills(text)

            if "No skills detected" in skills_output and session.resume and session.resume.chunks_json:
                chunks = session.resume.chunks_json
                chunk_texts = [c.get("text", c.get("content", str(c))) for c in chunks[:5]] \
                    if isinstance(chunks, list) and chunks else []
                skills_output = hybrid_extract_skills("", chunks=chunk_texts)

            self._save_conversation(session_id, user_message, skills_output)
            return skills_output

        # === NEW ORDER: Build plan BEFORE resolving reference ===
        plan = self.build_execution_plan(intent, session)

        # Let the PLAN decide if we need to attach previous answer
        processed_message = self._resolve_reference(user_message, session_id, plan)

        rag_context = self._prepare_rag_context(session, processed_message, plan)
        verdict_section_text = self._prepare_verdict_context(session, intent, plan)

        if verdict_section_text is None and plan.get("use_verdict"):
            return "Please complete an interview first."

        return self._execute_llm_response(
            session_id, 
            processed_message, 
            rag_context, 
            verdict_section_text, 
            plan, 
            original_user_message=user_message
        )
    # -------------------------------------------------------------------------
    # Central Decision Engine
    # -------------------------------------------------------------------------
    def build_execution_plan(self, intent: str, session) -> dict:
        plan = {
            "intent": intent,
            "use_llm": True,
            "use_rag": False,
            "use_verdict": False,
            "needs_reference": False,
            "mode_instruction": "",
        }

        if intent == "skills":
            plan.update({"use_llm": False, "use_deterministic": True, "deterministic_handler": "skills_extractor",
                         "mode_instruction": "SKILLS EXTRACTION MODE"})
        elif intent == "pii":
            plan.update({"use_llm": False, "use_deterministic": True, "deterministic_handler": "pii_vault",
                         "mode_instruction": "PII EXTRACTION MODE"})
        elif intent == "refinement":
            plan.update({
                "use_llm": True,
                "use_rag": False,
                "use_verdict": False,
                "needs_reference": True,
                "mode_instruction": "REFINEMENT MODE: Simplify and clarify the PREVIOUS ANSWER only. Do not add new information, new examples, or change the domain. Keep the core meaning but make it shorter, clearer, and easier to say in an interview."
            })
        elif intent == "improvement":
            plan.update({
                "use_llm": True,
                "use_rag": True,
                "use_verdict": True,
                "needs_reference": True,
                "mode_instruction": (
                    "IMPROVEMENT MODE: Improve the previous answer using resume context and interview report. "
                    "Make it more structured, specific, and interview-ready while keeping the core meaning."
                ),
            })
        elif intent == "strategy":
            plan.update({"use_llm": True, "use_verdict": True, "use_rag": False,
                         "mode_instruction": "STRATEGY FRAMEWORK MODE: Provide a structured framework for answering this type of question."})
        elif intent == "example":
            plan.update({"use_llm": True, "use_verdict": True, "use_rag": True,
                         "mode_instruction": "INTERVIEW ANSWER MODE: Generate a realistic, speakable answer."})
        elif intent == "weakness":
            plan.update({"use_llm": True, "use_verdict": True, "use_rag": False,
                         "mode_instruction": "EXTRACTION MODE: List ONLY weaknesses from the report."})
        elif intent == "strength":
            plan.update({"use_llm": True, "use_verdict": True, "use_rag": False,
                         "mode_instruction": "EXTRACTION MODE: List ONLY strengths from the report."})
        elif intent == "resume":
            plan.update({"use_llm": True, "use_rag": True, "use_verdict": False,
                         "mode_instruction": "EXTRACTION MODE: Extract requested information from the RESUME CONTEXT only."})
        else:
            plan.update({"use_llm": True, "use_verdict": True, "use_rag": True,
                         "mode_instruction": "GENERAL MODE: Answer based directly on the interview report summary."})

        return plan

    def _handle_pii_deterministic(self, session, session_id: str, user_message: str) -> str:
        # ... your original code (unchanged) ...
        if not session.resume:
            final_response = "No resume context available to extract personal details."
        else:
            from backend.app.shared.utils.pii_helper import pii_vault
            mapping = pii_vault.get_mapping(str(session.resume_id))
            if not mapping:
                final_response = "I couldn't find any personal details (PII) linked to your resume."
            else:
                details = self._filter_pii_by_query(mapping, user_message)
                final_response = "Here are the details extracted securely from your resume:\n" + "\n".join(f"- {d}" for d in details)

        self._save_conversation(session_id, user_message, final_response)
        return final_response

    def _prepare_rag_context(self, session, user_message: str, plan: dict) -> str:
        if not plan.get("use_rag", False):
            return "NOT NEEDED"
        if not session.resume or not session.resume.chunks_json:
            return "No resume context available."

        # Search query ko clean karein - sirf pehle 10-15 words len
        search_query = " ".join(user_message.split()[:15])
    
        if plan["intent"] == "improvement":
            search_query = f"technical details about {search_query}"

        chunks = session.resume.chunks_json
        relevant_chunks = self.rag.retrieve_only(
            query=search_query, chunks=chunks, collection_name=f"res_{session.resume_id}", top_k=3
        )
        return "\n".join(relevant_chunks)[:800] # Context window thori kam rakhein for free tier

    def _prepare_verdict_context(self, session, intent: str, plan: dict):
        if not plan.get("use_verdict", False):
            return "IGNORE THIS SECTION"
        last_interview = self.db.query(ChatSession).filter(
            ChatSession.resume_id == session.resume_id,
            ChatSession.final_verdict.isnot(None)
        ).order_by(ChatSession.created_at.desc()).first()
        if not last_interview:
            return None

        sections = self._extract_verdict_sections(last_interview.final_verdict)
        if intent == "strength":
            sections["weaknesses"] = []
        elif intent == "weakness":
            sections["strengths"] = []
        return self._build_verdict_section_text(sections, intent)

    def _execute_llm_response(self, session_id: str, processed_message: str, rag_context: str, 
                              verdict_context: str, plan: dict, original_user_message: str) -> str:
        """Use processed_message for LLM, but save original_user_message to DB"""
        history_text = "" if plan.get("needs_reference") else self._build_history_text(session_id)

        prompt = COACHING_STRICT_PROMPT_TEMPLATE.format(
            verdict_section=verdict_context,
            resume_text=rag_context,
            user_message=processed_message,           # Use enriched message for LLM
            instruction=f"{plan['mode_instruction']}\n[HISTORY]:\n{history_text}",
        )

        raw_response = self.llm.invoke(prompt).content.strip().replace("```", "").strip()
        final_response = self._clean_response(raw_response)

        # Save ORIGINAL user message to keep history clean
        self._save_conversation(session_id, original_user_message, final_response)
        return final_response

    def _detect_intent(self, message: str) -> str:
        return self.intent_classifier.get_intent(message)

    def _build_history_text(self, session_id: str) -> str:
        history_msgs = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.desc()).limit(3).all()
        
        formatted = []
        for m in reversed(history_msgs):
            # 180 chars se kam karke 120 kar den
            formatted.append(f"- {m.role.upper()}: {m.content[:120]}...")
        return "\n".join(formatted)

    def _save_conversation(self, session_id: str, user_message: str, assistant_response: str):
        self.db.add_all([
            ChatMessage(session_id=session_id, role="user", content=user_message),
            ChatMessage(session_id=session_id, role="assistant", content=assistant_response),
        ])
        self.db.commit()

    # Keep all your original helper methods at the bottom (unchanged)
    def _filter_pii_by_query(self, mapping: dict, user_message: str) -> list:
        # ... your original code ...
        msg_lower = user_message.lower()
        details = []
        for token, original_value in mapping.items():
            if "name" in msg_lower and "PERSON" in token:
                details.append(f"Name: {original_value}")
            if "email" in msg_lower and "EMAIL_ADDRESS" in token:
                details.append(f"Email: {original_value}")
            if any(w in msg_lower for w in ["phone", "number", "contact"]):
                if "PHONE_NUMBER" in token:
                    details.append(f"Phone: {original_value}")
            if any(w in msg_lower for w in ["location", "address"]):
                if "LOCATION" in token:
                    details.append(f"Location: {original_value}")
            if any(w in msg_lower for w in ["organization", "company"]):
                if "ORGANIZATION" in token:
                    details.append(f"Organization: {original_value}")
        if not details:
            details = list(mapping.values())
        return list(set(details))

    def _normalize_text(self, text: str) -> str:
        text = re.sub(r"^[-*]\s*", "", text)
        text = text.lower()
        text = re.sub(r"[^a-z0-9 ]", "", text)
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
    
        # Isko increase karke 8-10 lines tak le jayen taake coaching answers poore milein
        return "\n".join(unique[:10])

    def _extract_verdict_sections(self, verdict_json_str: str) -> dict:
        try:
            verdict_data = json.loads(verdict_json_str)
        except:
            return {"weaknesses": [], "strengths": [], "score": None, "evaluation": ""}
        return {
            "weaknesses": verdict_data.get("weaknesses", []),
            "strengths": verdict_data.get("strengths", []),
            "score": verdict_data.get("score"),
            "evaluation": verdict_data.get("evaluation", ""),
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