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
 * Parse the raw verdict text into structured sections.
 * (Fallback for legacy plain text verdicts)
 */
function parseVerdictSections(rawText) {
    const sections = {
        overview: '',
        score: null,
        strengths: [],
        weaknesses: [],
        improvements: [],
        strategy: ''
    };

    const lines = rawText.split('\n').filter(line => line.trim() !== '');
    if (lines.length > 0) {
        const firstLine = lines[0];
        const nameMatch = firstLine.match(/^([A-Za-z]+)\s*[—–-]\s*(.*)/);
        if (nameMatch) {
            sections.candidateName = nameMatch[1].trim();
            sections.overview = nameMatch[2].trim();
        } else {
            sections.overview = firstLine;
        }
    }

    const fullText = rawText.replace(/\n/g, ' ');

    const scoreMatch = fullText.match(/Score\s*[:]?\s*(\d+)\s*\/\s*(\d+)/i);
    if (scoreMatch) {
        sections.score = { earned: parseInt(scoreMatch[1]), total: parseInt(scoreMatch[2]) };
    }

    const extractBulletList = (pattern) => {
        const match = fullText.match(pattern);
        if (!match) return [];
        const content = match[1] || '';
        return content
            .split(/\s*[-•*]\s*/)
            .map(item => item.trim())
            .filter(item => item.length > 0 && !item.match(/^(Strengths|Weaknesses|How to Improve|Answering Strategy Tip)/i));
    };

    sections.strengths = extractBulletList(/Strengths?\s*[:]?\s*(.*?)(?:Weaknesses|How to Improve|Answering Strategy Tip|$)/is);
    sections.weaknesses = extractBulletList(/Weaknesses?\s*[:]?\s*(.*?)(?:Strengths|How to Improve|Answering Strategy Tip|$)/is);
    sections.improvements = extractBulletList(/How to Improve\s*[:]?\s*(.*?)(?:Strengths|Weaknesses|Answering Strategy Tip|$)/is);

    const strategyMatch = fullText.match(/Answering Strategy Tip\s*[:]?\s*(.*?)(?:Strengths|Weaknesses|How to Improve|$)/is);
    if (strategyMatch) {
        sections.strategy = strategyMatch[1].trim();
    }

    if (sections.strengths.length === 0 && sections.weaknesses.length === 0 && sections.improvements.length === 0) {
        sections.overview = rawText;
    }

    return sections;
}

/**
 * Append a beautifully structured final verdict card.
 */
export function appendFinalVerdict(verdictData, avgScore) {
    let data;
    
    if (typeof verdictData === 'string') {
        try {
            data = JSON.parse(verdictData);
        } catch {
            data = parseVerdictSections(verdictData);
        }
    } else {
        data = verdictData;
    }

    const container = document.createElement('div');
    container.className = 'mt-8 verdict-card bg-white rounded-2xl border border-gray-200 shadow-lg overflow-hidden';

    const header = document.createElement('div');
    header.className = 'bg-gradient-to-r from-primary to-primary-dim p-5 text-white';
    
    const summary = data.overall_summary || data.overview || 'Interview completed';
    
    header.innerHTML = `
        <div class="flex items-center justify-between flex-wrap gap-3">
            <div>
                <h3 class="text-xl font-bold">Candidate</h3>
                <p class="text-sm opacity-90 mt-1">${summary}</p>
            </div>
            ${avgScore !== undefined && avgScore !== null ? `
                <div class="bg-white/20 backdrop-blur-sm rounded-xl px-4 py-2 text-center">
                    <div class="text-3xl font-bold">${avgScore}/10</div>
                    <div class="text-xs uppercase tracking-wider">Overall</div>
                </div>
            ` : ''}
        </div>
    `;

    const body = document.createElement('div');
    body.className = 'p-5 space-y-5';

    const addSection = (title, items, icon, colorClass = 'text-blue-600') => {
        if (!items || (Array.isArray(items) && items.length === 0)) return;
        
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
                const bullet = document.createElement('div');
                bullet.className = 'flex items-start gap-2';
                bullet.innerHTML = `
                    <span class="text-primary mt-1.5 w-1.5 h-1.5 rounded-full bg-primary shrink-0"></span>
                    <span class="text-sm text-gray-700">${item}</span>
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

    // Scores Section (if available)
    if (data.scores) {
        const scoreSection = document.createElement('div');
        scoreSection.className = 'border-b border-gray-100 pb-4';
        scoreSection.innerHTML = `
            <div class="flex items-center gap-2 mb-3">
                <span class="material-symbols-outlined text-indigo-600 text-[20px]">analytics</span>
                <h4 class="font-bold text-gray-800">Detailed Scores</h4>
            </div>
            <div class="grid grid-cols-3 gap-3 pl-7">
                ${createScoreBadge('Tech', data.scores.technical_knowledge)}
                ${createScoreBadge('Comm', data.scores.communication_skills)}
                ${createScoreBadge('Problem', data.scores.problem_solving)}
            </div>
        `;
        body.appendChild(scoreSection);
    }

    function createScoreBadge(label, score) {
        const color = score >= 7 ? 'bg-green-100 text-green-800' : score >= 4 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800';
        return `
            <div class="text-center p-2 rounded-lg ${color}">
                <div class="text-lg font-bold">${score ?? '?'}</div>
                <div class="text-[10px] uppercase tracking-wider">${label}</div>
            </div>
        `;
    }

    addSection('Strengths', data.strengths, 'thumb_up', 'text-green-600');
    addSection('Areas for Improvement', data.weaknesses, 'construction', 'text-amber-600');
    addSection('How to Improve', data['How to Improve'], 'lightbulb', 'text-blue-600');
    addSection('Answering Strategy', data['Answering Strategy Tip'], 'strategy', 'text-purple-600');

    if (!data.strengths && !data.weaknesses && !data['How to Improve'] && !data.scores && typeof verdictData === 'string') {
        const rawDiv = document.createElement('div');
        rawDiv.className = 'p-5 text-gray-700 whitespace-pre-wrap';
        rawDiv.innerText = verdictData;
        body.appendChild(rawDiv);
    }

    container.appendChild(header);
    container.appendChild(body);
    elements.conversationContainer.appendChild(container);
    scrollToBottom();
}