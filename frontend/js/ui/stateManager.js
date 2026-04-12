// frontend/js/ui/stateManager.js

import { elements } from './domElements.js';

/**
 * Show a specific state view and hide others.
 */
export function showState(stateElement) {
    document.querySelectorAll('.state-view').forEach(s => s.classList.add('hidden'));
    stateElement.classList.remove('hidden');
}

/**
 * Scroll conversation to bottom.
 */
export function scrollToBottom() {
    const container = elements.scrollContainer;
    if (container) {
        container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    }
}

/**
 * Clear all messages from conversation container.
 */
export function clearConversation() {
    elements.conversationContainer.innerHTML = '';
}

/**
 * Lock chat UI (disable input and submit).
 */
export function lockChat() {
    elements.answerInput.disabled = true;
    elements.submitAnswerBtn.disabled = true;
    elements.answerInput.placeholder = "This interview has concluded.";
    elements.answerInputBox.classList.add('opacity-60', 'pointer-events-none');
}

/**
 * Unlock chat UI for active session.
 */
export function unlockChat() {
    elements.answerInput.disabled = false;
    elements.submitAnswerBtn.disabled = true; // enabled when user types
    elements.answerInput.placeholder = "Type your answer here...";
    elements.answerInputBox.classList.remove('opacity-60', 'pointer-events-none');
}

/**
 * Update progress bar and text.
 */
export function updateProgress(currentQ, total = 5) {
    elements.questionProgressText.innerText = `Q${currentQ} of ${total}`;
    const percent = (currentQ / total) * 100;
    elements.questionProgressBar.style.width = `${percent}%`;
}