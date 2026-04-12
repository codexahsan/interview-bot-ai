// frontend/js/features/interview.js 

import { apiService } from '../api.js';
import { AppState, TOTAL_QUESTIONS } from '../core/state.js';
import { elements } from '../ui/domElements.js';
import {
    showState,
    clearConversation,
    unlockChat,
    lockChat,
    updateProgress,
    scrollToBottom,
} from '../ui/stateManager.js';
import {
    appendBotMessage,
    appendUserMessage,
    appendFeedback,
    appendFinalVerdict,
} from '../ui/conversation.js';
import { loadSidebarHistory } from '../ui/sidebar.js';

export async function startInterview() {
    if (!AppState.sessionId) {
        alert("No session found. Please upload a resume first.");
        return;
    }

    try {
        showState(elements.stateInterview);
        clearConversation();
        unlockChat();

        const res = await apiService.startInterview(AppState.sessionId);
        appendBotMessage(res.data.question);
        updateProgress(1, TOTAL_QUESTIONS);
        await loadSidebarHistory();
    } catch (error) {
        alert("Failed to start interview: " + error.message);
        showState(elements.stateSummary);
    }
}

export async function submitAnswer() {
    const answer = elements.answerInput.value.trim();
    if (!answer || !AppState.sessionId) return;

    appendUserMessage(answer);
    elements.answerInput.value = '';
    elements.submitAnswerBtn.disabled = true;
    elements.answerInput.disabled = true;

    try {
        const res = await apiService.submitAnswer(AppState.sessionId, answer);
        const data = res.data;

        if (data.ans_tip || data.feedback) {
            appendFeedback(data.ans_tip || data.feedback);
        }

        if (data.is_active === false || data.status === "completed") {
            lockChat();
            appendFinalVerdict(data.final_verdict, data.average_score);
        } else {
            appendBotMessage(data.question);
            updateProgress(data.question_number, TOTAL_QUESTIONS);
            unlockChat();
            elements.answerInput.focus();
        }

        await loadSidebarHistory();
    } catch (error) {
        console.error("Submit failed:", error);
        alert("Failed to submit answer. Please try again.");
        unlockChat();
    }
}

export async function endSessionManually() {
    if (!AppState.sessionId) return;

    if (confirm("Are you sure you want to end this interview session early?")) {
        try {
            lockChat();
            elements.endSessionBtn.disabled = true;
            elements.answerInput.placeholder = "Generating Final Verdict...";

            const res = await apiService.finalizeInterview(AppState.sessionId);
            const data = res.data;

            appendFinalVerdict(data.final_verdict, data.average_score);
            await loadSidebarHistory();
        } catch (error) {
            console.error("Failed to end session:", error);
            alert("Failed to finalize interview: " + error.message);
            unlockChat();
            elements.endSessionBtn.disabled = false;
        }
    }
}

export async function loadSpecificChat(sessionId) {
    try {
        AppState.sessionId = sessionId;
        const res = await apiService.getSessionDetails(sessionId);
        const data = res.data;

        showState(elements.stateInterview);
        clearConversation();

        let qCount = 0;
        data.messages.forEach(msg => {
            if (msg.role === 'user') {
                appendUserMessage(msg.content);
                if (msg.ans_tip) appendFeedback(msg.ans_tip);
            } else {
                appendBotMessage(msg.content);
                qCount++;
            }
        });

        updateProgress(qCount || 1, TOTAL_QUESTIONS);

        if (data.is_active === false) {
            lockChat();
            if (data.final_verdict) {
                const avg = data.total_score / data.question_count;
                appendFinalVerdict(data.final_verdict, avg);
            }
        } else {
            unlockChat();
        }

        await loadSidebarHistory();
    } catch (error) {
        console.error("Failed to load session:", error);
        alert("Could not load this chat session.");
    }
}

export function initInterviewListeners() {
    elements.startInterviewBtn.addEventListener('click', startInterview);
    elements.submitAnswerBtn.addEventListener('click', submitAnswer);
    elements.endSessionBtn.addEventListener('click', endSessionManually);
    elements.answerInput.addEventListener('input', () => {
        elements.submitAnswerBtn.disabled = elements.answerInput.value.trim() === '';
    });
}