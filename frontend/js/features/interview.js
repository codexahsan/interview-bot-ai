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
} from '../ui/stateManager.js';
import {
    appendBotMessage,
    appendUserMessage,
    appendFeedback,
    appendFinalVerdict,
} from '../ui/conversation.js';
import { loadSidebarHistory } from '../ui/sidebar.js';
import { showToast } from '../ui/toast.js';
import { showConfirmModal } from '../ui/modal.js';

/**
 * Extract verdict object from various possible response formats.
 * Returns an object containing evaluation, score, strengths, weaknesses,
 * how_to_improve, and answering_strategy_tip.
 */
function extractVerdictObject(verdictData) {
    if (!verdictData) return null;

    // If it's a string, try to parse as JSON
    if (typeof verdictData === 'string') {
        let jsonStr = verdictData;
        // Remove possible markdown code fences
        jsonStr = jsonStr.replace(/```json\s*/gi, '').replace(/```\s*/g, '').trim();
        try {
            const parsed = JSON.parse(jsonStr);
            return parsed;
        } catch {
            // Not JSON, return null
            return null;
        }
    }

    // Already an object
    return verdictData;
}

export async function startInterview() {
    if (!AppState.sessionId) {
        showToast("No session found. Please upload a resume first.", 'warning');
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
        showToast("Failed to start interview: " + error.message, 'error');
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
        const payload = res.data.data || res.data;
        const data = payload;

        if (data.ans_tip || data.feedback) {
            appendFeedback(data.ans_tip || data.feedback);
        }

        if (data.is_active === false || data.status === "completed") {
            lockChat();
            const verdictObj = extractVerdictObject(data.final_verdict);
            const avgScore = data.average_score ?? 0;
            appendFinalVerdict(verdictObj, avgScore);
        } else {
            appendBotMessage(data.question);
            updateProgress(data.question_number, TOTAL_QUESTIONS);
            unlockChat();
            elements.answerInput.focus();
        }

        await loadSidebarHistory();
    } catch (error) {
        console.error("Submit failed:", error);
        showToast("Failed to submit answer. Please try again.", 'error');
        unlockChat();
    }
}

export async function endSessionManually() {
    if (!AppState.sessionId) return;

    const confirmed = await showConfirmModal({
        title: 'End Interview',
        message: 'Are you sure you want to end this interview early? The final verdict will be generated.',
        confirmText: 'End Interview',
        cancelText: 'Continue',
        type: 'warning'
    });

    if (!confirmed) return;

    try {
        lockChat();
        elements.endSessionBtn.disabled = true;
        elements.answerInput.placeholder = "Generating Final Verdict...";

        const res = await apiService.finalizeInterview(AppState.sessionId);
        const payload = res.data.data || res.data;
        const data = payload;

        const verdictObj = extractVerdictObject(data.final_verdict);
        const avgScore = data.average_score ?? 0;

        appendFinalVerdict(verdictObj, avgScore);
        await loadSidebarHistory();
    } catch (error) {
        console.error("Failed to end session:", error);
        showToast("Failed to finalize interview: " + error.message, 'error');
        unlockChat();
        elements.endSessionBtn.disabled = false;
    }
}

export async function loadSpecificChat(sessionId) {
    try {
        AppState.sessionId = sessionId;
        const res = await apiService.getSessionDetails(sessionId);
        const payload = res.data.data || res.data;
        const data = payload;

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
                const verdictObj = extractVerdictObject(data.final_verdict);
                const avgScore = data.total_score / data.question_count;
                appendFinalVerdict(verdictObj, avgScore);
            }
        } else {
            unlockChat();
        }

        await loadSidebarHistory();
    } catch (error) {
        console.error("Failed to load session:", error);
        showToast("Could not load this chat session.", 'error');
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