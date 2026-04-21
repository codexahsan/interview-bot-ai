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
import { showToast } from '../ui/toast.js';
import { showConfirmModal } from '../ui/modal.js';


// ============================================================================
//  AUTO-RESIZE TEXTAREA
// ============================================================================
function autoResizeTextarea() {
    const textarea = elements.answerInput;
    if (!textarea) return;
    
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// ============================================================================
//  TYPING INDICATOR (three-dot animation)
// ============================================================================
let interviewTypingIndicator = null;

function showInterviewTypingIndicator() {
    if (interviewTypingIndicator) return;

    const container = elements.conversationContainer;
    const div = document.createElement('div');
    div.className = 'flex items-start gap-4 mr-12 group';
    div.id = 'interview-typing-indicator';
    div.innerHTML = `
        <div class="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary-dim flex items-center justify-center shrink-0 shadow-md shadow-primary/20 mt-1">
            <span class="material-symbols-outlined text-white text-[20px]" style="font-variation-settings: 'FILL' 1;">smart_toy</span>
        </div>
        <div class="bg-surface-container-lowest p-4 rounded-2xl rounded-tl-sm shadow-sm border border-outline-variant/10">
            <div class="flex items-center gap-1.5 px-1">
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
            </div>
        </div>
    `;
    container.appendChild(div);
    interviewTypingIndicator = div;
    scrollToBottom(); // Uses imported function, which scrolls elements.scrollContainer
}

function hideInterviewTypingIndicator() {
    if (interviewTypingIndicator) {
        interviewTypingIndicator.remove();
        interviewTypingIndicator = null;
    }
}

// ============================================================================
//  UTILITY FUNCTIONS
// ============================================================================
function extractVerdictObject(verdictData) {
    if (!verdictData) return null;
    if (typeof verdictData === 'string') {
        let jsonStr = verdictData;
        jsonStr = jsonStr.replace(/```json\s*/gi, '').replace(/```\s*/g, '').trim();
        try {
            return JSON.parse(jsonStr);
        } catch {
            return null;
        }
    }
    return verdictData;
}

// ============================================================================
//  UI MODE SWITCHING
// ============================================================================
function switchToCoachMode(sessionId) {
    const btn = elements.endSessionBtn;
    btn.textContent = 'Talk to AI Coach';
    btn.className = 'px-3 sm:px-4 py-1.5 sm:py-2 border-2 border-primary/30 text-primary text-xs font-bold rounded-lg hover:bg-primary hover:text-white transition-all duration-300';

    const newBtn = btn.cloneNode(true);
    newBtn.disabled = false;
    btn.parentNode.replaceChild(newBtn, btn);
    elements.endSessionBtn = newBtn;

    newBtn.addEventListener('click', async () => {
        const module = await import('../features/coaching.js');
        module.startCoachingSession(sessionId);
    });
}

function switchToEndInterviewMode() {
    const btn = elements.endSessionBtn;
    btn.textContent = 'End Interview';
    btn.className = 'px-3 sm:px-4 py-1.5 sm:py-2 border-2 border-error/20 text-error text-xs font-bold rounded-lg hover:bg-error hover:text-white transition-all duration-300';

    const newBtn = btn.cloneNode(true);
    newBtn.disabled = false;
    btn.parentNode.replaceChild(newBtn, btn);
    elements.endSessionBtn = newBtn;

    newBtn.addEventListener('click', endSessionManually);
}

// ============================================================================
//  CORE INTERVIEW FLOW
// ============================================================================
export async function startInterview() {
    if (!AppState.sessionId) {
        showToast("No session found. Please upload a resume first.", 'warning');
        return;
    }

    const btn = elements.startInterviewBtn;
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = `
        <span class="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
        Generating...
    `;

    try {
        const res = await apiService.startInterview(AppState.sessionId);
        
        showState(elements.stateInterview);
        clearConversation();
        unlockChat();
        switchToEndInterviewMode();
        
        appendBotMessage(res.data.question);
        updateProgress(1, TOTAL_QUESTIONS);
        await loadSidebarHistory();
    } catch (error) {
        showToast("Failed to start interview: " + error.message, 'error');
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

export async function submitAnswer() {
    const answer = elements.answerInput.value.trim();
    if (!answer || !AppState.sessionId) return;

    appendUserMessage(answer);
    elements.answerInput.value = '';
    autoResizeTextarea();
    elements.submitAnswerBtn.disabled = true;
    elements.answerInput.disabled = true;

    showInterviewTypingIndicator();

    try {
        const res = await apiService.submitAnswer(AppState.sessionId, answer);
        const payload = res.data.data || res.data;
        const data = payload;

        hideInterviewTypingIndicator();

        if (data.ans_tip || data.feedback) {
            appendFeedback(data.ans_tip || data.feedback);
        }

        if (data.is_active === false || data.status === "completed") {
            lockChat();
            const verdictObj = extractVerdictObject(data.final_verdict);
            const avgScore = data.average_score ?? 0;
            appendFinalVerdict(verdictObj, avgScore);
            switchToCoachMode(AppState.sessionId);
        } else {
            appendBotMessage(data.question);
            updateProgress(data.question_number, TOTAL_QUESTIONS);
            unlockChat();
            elements.answerInput.focus();
        }

        await loadSidebarHistory();
    } catch (error) {
        hideInterviewTypingIndicator();
        console.error("Submit failed:", error);
        const errorMessage = error.message || "Failed to submit answer. Please try again.";
        showToast(errorMessage, 'error');
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
        switchToCoachMode(AppState.sessionId);
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

        if (data.session_type === 'coaching') {
            const module = await import('../features/coaching.js');
            module.loadCoachingSession(sessionId, data);
            return;
        }

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
            switchToCoachMode(sessionId);
            if (data.final_verdict) {
                const verdictObj = extractVerdictObject(data.final_verdict);
                const avgScore = data.total_score / data.question_count;
                appendFinalVerdict(verdictObj, avgScore);
            }
        } else {
            unlockChat();
            switchToEndInterviewMode();
        }

        await loadSidebarHistory();
    } catch (error) {
        console.error("Failed to load session:", error);
        showToast("Could not load this chat session.", 'error');
    }
}

// ============================================================================
//  INITIALIZATION
// ============================================================================
export function initInterviewListeners() {
    elements.startInterviewBtn.addEventListener('click', startInterview);
    elements.submitAnswerBtn.addEventListener('click', submitAnswer);
    elements.endSessionBtn.addEventListener('click', endSessionManually);
    elements.answerInput.addEventListener('input', autoResizeTextarea);
    
    elements.answerInput.addEventListener('input', () => {
        elements.submitAnswerBtn.disabled = elements.answerInput.value.trim() === '';
    });
    
    elements.answerInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!elements.submitAnswerBtn.disabled) {
                submitAnswer();
            }
        }
    });
}