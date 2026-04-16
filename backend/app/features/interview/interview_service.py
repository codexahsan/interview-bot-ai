# backend/app/features/interview/interview_service.py

"""
Service layer for interview orchestration.
Handles question generation, answer evaluation, scoring, tips, and final verdict.
Now persists all conversation turns and enforces session active status.
Uses Redis for fast state access and reduces DB hits.
"""

import re
import json
from sqlalchemy.orm import Session

from backend.app.shared.llm.client import get_llm
from pydantic import BaseModel, Field
from backend.app.features.interview.interview_prompts import (
    INTERVIEW_QUESTION_PROMPT,
    NEXT_QUESTION_PROMPT,
    EVALUATION_PROMPT,
)
from backend.app.features.chat.chat_models import ChatSession, ChatMessage
from backend.app.constants import (
    INTERVIEW_CONTEXT_LENGTH_LIMIT,
    INTERVIEW_MAX_QUESTIONS,
    INTERVIEW_FALLBACK_SCORE,
    INTERVIEW_SCORE_REGEX_PATTERN,
    INTERVIEW_TIP_REGEX_PATTERN,
    ERR_NO_RESUME_FOR_SESSION,
    ERR_INVALID_SESSION,
    FINAL_VERDICT_PROMPT,
    INTERVIEW_TOPICS,   
)
from backend.app.core.logger import get_logger
from backend.app.core.redis_client import get_redis

logger = get_logger(__name__)


# ==========================================
# 🎯 STRICT SCHEMA DEFINITION
# ==========================================
class FinalVerdictSchema(BaseModel):
    """Strict JSON schema for the final interview verdict."""
    evaluation: str = Field(description="A concise 1-line overall performance summary.")
    score: float = Field(description="The numerical score out of 10.")
    strengths: list[str] = Field(description="List of maximum 2 strengths, each max 1 line.")
    weaknesses: list[str] = Field(description="List of maximum 2 weaknesses, each max 1 line.")
    how_to_improve: list[str] = Field(description="List of maximum 2 areas to improve, each max 1 line.")
    answering_strategy_tip: str = Field(description="A single tip on answering strategy.")


class InterviewService:
    """Handles the interview question flow and evaluation."""

    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm()
        self.redis = get_redis()

        self.structured_llm = self.llm.with_structured_output(FinalVerdictSchema)

    def _generate_title_from_question(self, question: str) -> str:
        """Generate a short 3-5 word title from the first interview question."""
        prompt = f"""
        Convert this interview question into a short 3-5 word title. Return only the title, no quotes or extra text.

        Question:
        {question}
        """
        try:
            response = self.llm.invoke(prompt).content.strip()
            # Clean up any stray quotes or newlines
            title = response.replace('"', '').replace("'", '').strip()
            return title[:50]  # limit length
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
            return "Interview Session"

    def start_interview(self, session_id: str) -> dict:
        """
        Generate the first interview question based on the resume.
        Also stores the assistant's question in the chat history and sets a title.
        Caches session state in Redis.

        Args:
            session_id: Chat session UUID.

        Returns:
            Dict containing the question and question number, or error.
        """
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

        if not session or not session.resume:
            logger.warning(f"Start interview failed: no resume for session {session_id}")
            return {"error": ERR_NO_RESUME_FOR_SESSION}

        if not session.is_active:
            logger.warning(f"Attempt to start an inactive session {session_id}")
            return {"error": "Interview session is inactive."}

        context = session.resume.masked_text[:INTERVIEW_CONTEXT_LENGTH_LIMIT]
        # Start with first topic
        first_topic = INTERVIEW_TOPICS[0]
        
        prompt = INTERVIEW_QUESTION_PROMPT.format(
            context=context,
            topic=first_topic        # <-- pass topic
        )

        question = self.llm.invoke(prompt).content.strip()
        logger.info(f"Generated first question for session {session_id}")

        # Auto-generate title if not already set
        if not session.title:
            session.title = self._generate_title_from_question(question)

        # Update session state in DB
        session.current_question = question
        session.question_count = 1
        session.total_score = 0

        # Persist assistant message to chat history
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=question
        )
        self.db.add(assistant_msg)

        self.db.commit()
        logger.debug(f"First question saved to chat_messages for session {session_id}")

        # Cache session state in Redis
        self.redis.set(
            f"session:{session_id}",
            json.dumps({
                "current_question": question,
                "question_count": 1,
                "total_score": 0,
                "is_active": True,
                "covered_topics": [first_topic],
            }),
            ex=7200
        )

        # Invalidate chat history cache
        self.redis.delete(f"chat_history:{session_id}")

        return {
            "question": question,
            "question_number": 1
        }

    def submit_answer(self, session_id: str, answer: str) -> dict:
        """
        Evaluate the answer, update score, provide a tip, and either provide feedback
        with next question or complete the interview with a final verdict.
        Also stores the user's answer (with tip) and the assistant's next question (if any)
        in the chat history. Uses Redis for state management.

        Args:
            session_id: Chat session UUID.
            answer: Candidate's answer text.

        Returns:
            Dict with evaluation, next question, tip, or final summary.
        """
        # Try Redis first for session state
        session_data = self.redis.get(f"session:{session_id}")
        if session_data:
            session_data = json.loads(session_data)
            # Fetch full DB session object for relationships and persistence
            session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                # Sync Redis data to DB object (in case of drift)
                session.current_question = session_data.get("current_question")
                session.question_count = session_data.get("question_count", 0)
                session.total_score = session_data.get("total_score", 0)
                session.is_active = session_data.get("is_active", True)
        else:
            # Fallback to DB
            session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                session_data = {
                    "current_question": session.current_question,
                    "question_count": session.question_count,
                    "total_score": session.total_score,
                    "is_active": session.is_active
                }

        # --- CHECK: If interview is already completed ---
        if not session or not session.is_active:
            return {
                "error": "This interview has already been completed.",
                "is_active": False,
                "final_verdict": session.final_verdict if session else None,
                "total_score": session.total_score if session else 0
            }

        if not session.resume:
            logger.warning(f"Submit answer failed: invalid session {session_id}")
            return {"error": ERR_INVALID_SESSION}

        current_question = session.current_question

        # --- Persist user's answer (tip will be updated later) ---
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=answer
        )
        self.db.add(user_msg)
        self.db.flush()  # Assign ID without committing yet
        logger.debug(f"User answer saved for session {session_id}")

        # --- Evaluate Answer + Extract Tip ---
        eval_prompt = EVALUATION_PROMPT.format(
            question=current_question,
            answer=answer
        )
        evaluation = self.llm.invoke(eval_prompt).content.strip()
        logger.debug(f"Evaluation received for session {session_id}")

        # Extract score and tip
        score = self._extract_score(evaluation)
        tip = self._extract_tip(evaluation)

        session.total_score += score
        user_msg.ans_tip = tip  # Save tip in user message row

        # --- TRIGGER: Check if this was the last question ---
        if session.question_count >= INTERVIEW_MAX_QUESTIONS:
            result = self._finalize_interview(session, evaluation, tip)
            # Clear Redis session key as interview is completed
            self.redis.delete(f"session:{session_id}")
            self.redis.delete(f"chat_history:{session_id}")
            return result

        # --- Generate next question (if not last) ---
        context = session.resume.masked_text[:INTERVIEW_CONTEXT_LENGTH_LIMIT]
        history = f"Q: {current_question}\nA: {answer}"

        # Get covered topics from Redis cache
        covered_topics = session_data.get("covered_topics", [INTERVIEW_TOPICS[0]])

        # Pick next topic (cycle through INTERVIEW_TOPICS)
        current_index = len(covered_topics)  # question_count is already incremented after this
        next_topic = INTERVIEW_TOPICS[min(current_index, len(INTERVIEW_TOPICS) - 1)]

        next_prompt = NEXT_QUESTION_PROMPT.format(
            context=context,
            history=history,
            covered_topics=", ".join(covered_topics),
            next_topic=next_topic,
        )

        next_question = self.llm.invoke(next_prompt).content.strip()
        logger.info(f"Generated question #{session.question_count + 1} (topic: {next_topic}) for session {session_id}")


        # Persist assistant's next question
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=next_question
        )
        self.db.add(assistant_msg)

        # Update session state
        session.current_question = next_question
        session.question_count += 1

        self.db.commit()
        logger.debug(f"Next question saved to chat_messages for session {session_id}")

        # Update Redis — add new topic to covered list
        updated_topics = covered_topics + [next_topic]

        self.redis.set(
            f"session:{session_id}",
            json.dumps({
                "current_question": next_question,
                "question_count": session.question_count,
                "total_score": session.total_score,
                "is_active": True,
                "covered_topics": updated_topics,
            }),
            ex=7200
        )
        # Invalidate chat history cache
        self.redis.delete(f"chat_history:{session_id}")

        return {
            "status": "ongoing",
            "question": next_question,
            "question_number": session.question_count,
            "feedback": evaluation,
            "ans_tip": tip,
            "is_active": True
        }

    def end_interview_manually(self, session_id: str) -> dict:
        """
        Manually end the interview before reaching the max questions limit.
        """
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

        if not session:
            return {"error": ERR_INVALID_SESSION}
        
        if not session.is_active:
            return {
                "error": "This interview has already been completed.",
                "is_active": False,
                "final_verdict": session.final_verdict,
                "total_score": session.total_score
            }

        logger.info(f"Manually forcing end for session {session_id}")
        
        result = self._finalize_interview(
            session=session, 
            last_feedback="Session was manually concluded by the user.", 
            last_tip="N/A"
        )
        # Clear Redis keys
        self.redis.delete(f"session:{session_id}")
        self.redis.delete(f"chat_history:{session_id}")
        return result

    def _finalize_interview(self, session: ChatSession, last_feedback: str, last_tip: str) -> dict:
        """
        Generate final verdict, close session, and return completion data.
        """
        candidate_name = "Candidate"
        if session.resume and getattr(session.resume, 'candidate_name', None):
            candidate_name = session.resume.candidate_name

        messages = session.messages 
        history_lines = []
        for m in messages:
            role_label = "Interviewer" if m.role == "assistant" else "Candidate"
            history_lines.append(f"{role_label}: {m.content}")
        
        history_text = "\n".join(history_lines)

        try:
            verdict_prompt = FINAL_VERDICT_PROMPT.format(
                Name=candidate_name,
                history=history_text
            )
            # 🚀 Use the Structured LLM here
            verdict_obj = self.structured_llm.invoke(verdict_prompt)
            
            # Convert Pydantic object to JSON string for Database
            verdict = verdict_obj.model_dump_json()
            
        except KeyError as e:
            logger.error(f"Prompt formatting error: {e}")
            verdict = f'{{"evaluation": "{candidate_name} — Overall, formatting error occurred."}}'
        except Exception as e:
            logger.error(f"LLM Verdict generation failed: {e}")
            verdict = f'{{"evaluation": "{candidate_name} — Overall, interview concluded but could not generate detailed report."}}'

        # Lock session and save
        session.is_active = False  
        session.final_verdict = verdict

        # Calculate average score
        avg_score = 0
        if session.question_count > 0:
            avg_score = float(f"{session.total_score / session.question_count:.1f}")
            
        logger.info(f"Interview completed for session {session.id}, avg score: {avg_score}")

        self.db.commit()

        # Clear Redis session cache
        self.redis.delete(f"session:{session.id}")
        self.redis.delete(f"chat_history:{session.id}")

        return {
            "status": "completed",
            "average_score": avg_score,
            "final_verdict": verdict, 
            "last_feedback": last_feedback,
            "ans_tip": last_tip,
            "is_active": False
        }

    def _extract_score(self, evaluation_text: str) -> int:
        """
        Parse the numerical score from LLM evaluation text.
        """
        match = re.search(INTERVIEW_SCORE_REGEX_PATTERN, evaluation_text)
        if match:
            try:
                score = int(match.group(1))
                logger.debug(f"Extracted score: {score}/10")
                return score
            except ValueError:
                pass

        logger.warning(f"Could not parse score from evaluation, using fallback {INTERVIEW_FALLBACK_SCORE}")
        return INTERVIEW_FALLBACK_SCORE

    def _extract_tip(self, text: str) -> str:
        """
        Extract the actionable tip from LLM evaluation text.
        """
        match = re.search(INTERVIEW_TIP_REGEX_PATTERN, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "Keep practicing your technical communication."