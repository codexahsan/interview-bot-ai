// frontend/js/features/coaching.js 

import { apiService } from '../api.js';
import { AppState } from '../core/state.js';
import { elements } from '../ui/domElements.js';
import { showState, scrollToBottom, updateURL } from '../ui/stateManager.js';
import { showToast } from '../ui/toast.js';

let currentCoachingSessionId = null;

/**
 * Format a coaching message (may contain bullet points and paragraphs)
 * into structured HTML.
 */
function formatCoachingMessage(text) {
    if (!text) return '';
    
    const lines = text.split('\n').filter(line => line.trim() !== '');
    const result = [];
    let bulletItems = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        // Check if line starts with bullet marker
        if (line.match(/^[-*•]\s+/)) {
            // Remove the bullet marker and add to current bullet list
            const content = line.replace(/^[-*•]\s+/, '');
            bulletItems.push(content);
        } else {
            // If we have accumulated bullet items, flush them as a <ul>
            if (bulletItems.length > 0) {
                const ul = document.createElement('ul');
                ul.className = 'list-disc pl-5 space-y-1 text-xs leading-relaxed text-on-surface';
                bulletItems.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = item;
                    ul.appendChild(li);
                });
                result.push(ul);
                bulletItems = [];
            }
            // Add as a paragraph
            const p = document.createElement('p');
            p.className = 'text-xs leading-relaxed text-on-surface';
            p.textContent = line;
            result.push(p);
        }
    }
    
    // Flush any remaining bullet items
    if (bulletItems.length > 0) {
        const ul = document.createElement('ul');
        ul.className = 'list-disc pl-5 space-y-1 text-xs leading-relaxed text-on-surface';
        bulletItems.forEach(item => {
            const li = document.createElement('li');
            li.textContent = item;
            ul.appendChild(li);
        });
        result.push(ul);
    }
    
    // If no elements were created, fallback to plain text
    if (result.length === 0) {
        const p = document.createElement('p');
        p.className = 'text-xs leading-relaxed text-on-surface';
        p.textContent = text;
        result.push(p);
    }
    
    return result;
}

/**
 * Append a coach (assistant) message with structured formatting.
 */
function appendCoachMessage(text) {
    const container = elements.coachingConversationContainer;
    const div = document.createElement('div');
    div.className = 'flex items-start gap-3';
    
    // Create message bubble
    const bubble = document.createElement('div');
    bubble.className = 'bg-surface-container-lowest p-3.5 rounded-xl rounded-tl-sm shadow-sm border border-outline-variant/10 flex-1';
    
    // Apply structured formatting
    const formattedElements = formatCoachingMessage(text);
    if (Array.isArray(formattedElements)) {
        formattedElements.forEach(el => bubble.appendChild(el));
    } else {
        bubble.innerHTML = `<p class="text-xs leading-relaxed text-on-surface">${text}</p>`;
    }
    
    div.innerHTML = `
        <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shrink-0 shadow-sm">
            <span class="material-symbols-outlined text-white text-[14px]">school</span>
        </div>
    `;
    div.querySelector('.w-7').parentNode.appendChild(bubble);
    
    container.appendChild(div);
    scrollToBottom(elements.coachingScrollContainer);
}

function appendUserCoachingMessage(text) {
    const container = elements.coachingConversationContainer;
    const div = document.createElement('div');
    div.className = 'flex items-start gap-3 flex-row-reverse';
    div.innerHTML = `
        <div class="w-7 h-7 rounded-full bg-surface-container-highest border border-outline-variant/30 flex items-center justify-center shrink-0">
            <span class="material-symbols-outlined text-on-surface-variant text-[16px]">person</span>
        </div>
        <div class="bg-primary-container/20 p-3.5 rounded-xl rounded-tr-sm ghost-border">
            <p class="text-xs leading-relaxed text-on-surface-variant">${text}</p>
        </div>
    `;
    container.appendChild(div);
    scrollToBottom(elements.coachingScrollContainer);
}

export async function startCoachingSession(interviewSessionId) {
    try {
        showToast('Starting AI Coach...', 'info');
        
        const res = await apiService.startCoachingSession(interviewSessionId);
        const data = res.data;
        
        currentCoachingSessionId = data.coaching_session_id;
        AppState.coachingSessionId = currentCoachingSessionId;
        AppState.sessionId = currentCoachingSessionId;
        updateURL(currentCoachingSessionId);
        
        elements.coachingConversationContainer.innerHTML = '';
        showState(elements.stateCoaching);
        
        const welcome = data.welcome_message || "Hi! I'm your AI coach. How can I help you improve?";
        appendCoachMessage(welcome);
        
        elements.coachingMessageInput.disabled = false;
        elements.sendCoachingMessageBtn.disabled = true;
        
        showToast('Coach is ready!', 'success');
    } catch (error) {
        showToast('Failed to start coaching: ' + error.message, 'error');
    }
}

async function sendCoachingMessage() {
    const message = elements.coachingMessageInput.value.trim();
    if (!message || !currentCoachingSessionId) return;

    appendUserCoachingMessage(message);
    elements.coachingMessageInput.value = '';
    elements.sendCoachingMessageBtn.disabled = true;
    elements.coachingMessageInput.disabled = true;

    try {
        const res = await apiService.sendCoachingMessage(currentCoachingSessionId, message);
        const data = res.data;
        appendCoachMessage(data.answer);
    } catch (error) {
        showToast('Failed to get response: ' + error.message, 'error');
    } finally {
        elements.coachingMessageInput.disabled = false;
        elements.coachingMessageInput.focus();
    }
}

export function initCoachingListeners() {
    elements.sendCoachingMessageBtn.addEventListener('click', sendCoachingMessage);
    
    elements.coachingMessageInput.addEventListener('input', () => {
        elements.sendCoachingMessageBtn.disabled = elements.coachingMessageInput.value.trim() === '';
    });
    
    elements.coachingMessageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!elements.sendCoachingMessageBtn.disabled) {
                sendCoachingMessage();
            }
        }
    });
    
    elements.endCoachingBtn.addEventListener('click', () => {
        showState(elements.stateUpload);
        currentCoachingSessionId = null;
        updateURL(null);
    });
}

export function loadCoachingSession(sessionId, data) {
    currentCoachingSessionId = sessionId;
    AppState.coachingSessionId = sessionId;
    AppState.sessionId = sessionId;
    updateURL(sessionId);

    showState(elements.stateCoaching);
    elements.coachingConversationContainer.innerHTML = '';

    data.messages.forEach(msg => {
        if (msg.role === 'user') {
            appendUserCoachingMessage(msg.content);
        } else {
            appendCoachMessage(msg.content);
        }
    });

    elements.coachingMessageInput.disabled = false;
    elements.sendCoachingMessageBtn.disabled = true;

    showToast('Coaching session loaded', 'success');
}