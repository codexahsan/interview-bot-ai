// frontend/js/ui/conversation.js

import { elements } from './domElements.js';
import { scrollToBottom } from './stateManager.js';

/**
 * Append an assistant (bot) message.
 */
export function appendBotMessage(text) {
    const div = document.createElement('div');
    div.className = 'flex items-start gap-4 mr-12 group';
    div.innerHTML = `
        <div class="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-primary-dim flex items-center justify-center shrink-0 shadow-md shadow-primary/20 mt-1">
            <span class="material-symbols-outlined text-white text-[20px]" style="font-variation-settings: 'FILL' 1;">smart_toy</span>
        </div>
        <div class="bg-surface-container-lowest p-6 rounded-2xl rounded-tl-sm shadow-sm border border-outline-variant/10 relative">
            <span class="absolute -left-2 top-4 w-4 h-4 bg-surface-container-lowest rotate-45 border-l border-t border-outline-variant/10"></span>
            <p class="text-[0.95rem] leading-relaxed text-on-surface font-medium relative z-10">"${text}"</p>
        </div>`;
    elements.conversationContainer.appendChild(div);
    scrollToBottom();
}

/**
 * Append a user message.
 */
export function appendUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'flex items-start gap-4 ml-12 flex-row-reverse group';
    div.innerHTML = `
        <div class="w-10 h-10 rounded-full bg-surface-container-highest border border-outline-variant/30 shrink-0 flex items-center justify-center mt-1">
            <span class="material-symbols-outlined text-on-surface-variant text-[20px]">person</span>
        </div>
        <div class="bg-primary-container/20 p-6 rounded-2xl rounded-tr-sm ghost-border relative">
            <span class="absolute -right-2 top-4 w-4 h-4 bg-primary-fixed-dim/20 rotate-45 border-r border-t border-outline-variant/10"></span>
            <p class="text-[0.9rem] leading-relaxed text-on-surface-variant relative z-10">"${text}"</p>
        </div>`;
    elements.conversationContainer.appendChild(div);
    scrollToBottom();
}

/**
 * Append feedback (pro-tip) message.
 */
export function appendFeedback(feedbackText) {
    if (!feedbackText) return;
    const div = document.createElement('div');
    div.className = 'ml-16 mr-12 p-5 bg-yellow-50 rounded-xl border border-yellow-100 shadow-sm relative overflow-hidden';
    div.innerHTML = `
        <div class="absolute left-0 top-0 bottom-0 w-1 bg-yellow-400"></div>
        <div class="flex items-center gap-2 mb-2">
            <span class="material-symbols-outlined text-yellow-600 text-[18px]">tips_and_updates</span>
            <span class="text-[11px] font-bold uppercase tracking-widest text-yellow-700">Pro-Tip</span>
        </div>
        <p class="text-sm text-yellow-800/80 leading-relaxed">${feedbackText}</p>`;
    elements.conversationContainer.appendChild(div);
    scrollToBottom();
}

/**
 * Fallback parser for plain text verdicts.
 */
function parsePlainTextVerdict(text) {
    const data = {
        evaluation: '',
        score: null,
        strengths: [],
        weaknesses: [],
        how_to_improve: [],
        answering_strategy_tip: ''
    };

    text = text.replace(/```json\s*/gi, '').replace(/```\s*/g, '');
    text = text.replace(/\\n/g, '\n').replace(/\\"/g, '"');

    const lines = text.split('\n').map(l => l.trim()).filter(l => l);
    if (lines.length > 0 && !lines[0].includes('🔹')) {
        data.evaluation = lines[0].replace(/^Overall,\s*/i, '').trim();
    }

    const scoreMatch = text.match(/🔹\s*Score\s*[:]?\s*(\d+)\s*\/\s*(\d+)/i);
    if (scoreMatch) {
        data.score = `${scoreMatch[1]}/${scoreMatch[2]}`;
    }

    const extractBullets = (sectionName) => {
        const regex = new RegExp(`🔹\\s*${sectionName}\\s*[:]?\\s*([\\s\\S]*?)(?=🔹|$)`, 'i');
        const match = text.match(regex);
        if (!match) return [];
        let content = match[1].trim();
        return content
            .split(/\n\s*[-•*]\s*|[-•*]\s+/)
            .map(item => item.trim())
            .filter(item => item && !item.startsWith('🔹'));
    };

    data.strengths = extractBullets('Strengths');
    data.weaknesses = extractBullets('Weaknesses');
    data.how_to_improve = extractBullets('How to Improve');
    data.answering_strategy_tip = extractBullets('Answering Strategy Tip').join(' ');

    return data;
}

/**
 * Append a beautifully structured final verdict card.
 */
export function appendFinalVerdict(verdictData, avgScore) {
    let data = verdictData;

    // Handle null or undefined
    if (!data) {
        data = { evaluation: 'Interview completed.' };
    }

    // If it's a string, try to parse as JSON
    if (typeof data === 'string') {
        try {
            data = JSON.parse(data);
        } catch {
            data = parsePlainTextVerdict(data);
        }
    }

    // ========== FLEXIBLE FIELD EXTRACTION ==========
    const evaluation = data.evaluation || data.overall_performance_summary || 'Interview completed';
    
    // Score can be a string like "38/50" or a number like 7.5
    const scoreRaw = data.score ?? null;
    const strengths = data.strengths || data.strength || [];
    // Handle multiple possible keys for weaknesses
    const weaknesses = data.weaknesses || data.weakness || data.areas_for_improvement || [];
    const improvements = data.how_to_improve || data.improvements || data.improvement || [];
    const strategy = data.answering_strategy_tip || data.strategy || data.answering_strategy || '';

    // Parse score into displayable format
    let parsedScore = null;
    if (scoreRaw !== null && scoreRaw !== undefined) {
        if (typeof scoreRaw === 'string') {
            const match = scoreRaw.match(/(\d+(?:\.\d+)?)\s*\/\s*(\d+)/);
            if (match) {
                parsedScore = { earned: parseFloat(match[1]), total: parseInt(match[2]) };
            } else {
                // Just a number string, treat as out of 10
                const num = parseFloat(scoreRaw);
                if (!isNaN(num)) parsedScore = { earned: num, total: 10 };
            }
        } else if (typeof scoreRaw === 'number') {
            parsedScore = { earned: scoreRaw, total: 10 };
        }
    }

    const container = document.createElement('div');
    container.className = 'mt-8 verdict-card bg-white rounded-2xl border border-gray-200 shadow-lg overflow-hidden';

    // ========== HEADER ==========
    const header = document.createElement('div');
    header.className = 'bg-gradient-to-r from-primary to-primary-dim p-5 text-white';
    header.innerHTML = `
        <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
                <h3 class="text-xl font-bold mb-1">Interview Feedback</h3>
                <p class="text-sm opacity-90 break-words">${evaluation}</p>
            </div>
            ${avgScore !== undefined && avgScore !== null ? `
                <div class="bg-white/20 backdrop-blur-sm rounded-xl px-4 py-2 text-center shrink-0">
                    <div class="text-3xl font-bold">${avgScore}/10</div>
                    <div class="text-xs uppercase tracking-wider">Overall</div>
                </div>
            ` : (parsedScore ? `
                <div class="bg-white/20 backdrop-blur-sm rounded-xl px-4 py-2 text-center shrink-0">
                    <div class="text-3xl font-bold">${parsedScore.earned}/${parsedScore.total}</div>
                    <div class="text-xs uppercase tracking-wider">Score</div>
                </div>
            ` : '')}
        </div>
    `;

    const body = document.createElement('div');
    body.className = 'p-5 space-y-5';

    const addSection = (title, items, icon, colorClass = 'text-blue-600') => {
        if (!items) return;
        if (Array.isArray(items) && items.length === 0) return;
        if (typeof items === 'string' && items.trim() === '') return;

        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'border-b border-gray-100 pb-4 last:border-0 last:pb-0';

        const titleDiv = document.createElement('div');
        titleDiv.className = 'flex items-center gap-2 mb-2';
        titleDiv.innerHTML = `
            <span class="material-symbols-outlined ${colorClass} text-[20px]">${icon}</span>
            <h4 class="font-bold text-gray-800">${title}</h4>
        `;

        const contentDiv = document.createElement('div');
        if (Array.isArray(items)) {
            contentDiv.className = 'grid grid-cols-1 gap-2 pl-7';
            items.forEach(item => {
                const cleanItem = String(item).replace(/^[-•*]\s*/, '').trim();
                const bullet = document.createElement('div');
                bullet.className = 'flex items-start gap-2';
                bullet.innerHTML = `
                    <span class="text-primary mt-1.5 w-1.5 h-1.5 rounded-full bg-primary shrink-0"></span>
                    <span class="text-sm text-gray-700">${cleanItem}</span>
                `;
                contentDiv.appendChild(bullet);
            });
        } else {
            contentDiv.className = 'pl-7 text-sm text-gray-700';
            contentDiv.innerHTML = `<p>${items}</p>`;
        }

        sectionDiv.appendChild(titleDiv);
        sectionDiv.appendChild(contentDiv);
        body.appendChild(sectionDiv);
    };

    addSection('Strengths', strengths, 'thumb_up', 'text-green-600');
    addSection('Areas for Improvement', weaknesses, 'construction', 'text-amber-600');
    addSection('How to Improve', improvements, 'lightbulb', 'text-blue-600');
    addSection('Answering Strategy', strategy, 'strategy', 'text-purple-600');

    container.appendChild(header);
    container.appendChild(body);
    elements.conversationContainer.appendChild(container);
    scrollToBottom();
}