// frontend/js/ui/sidebar.js

import { apiService } from '../api.js';
import { AppState } from '../core/state.js';
import { elements } from './domElements.js';
import { showState, updateURL } from './stateManager.js';
import { showToast } from './toast.js';
import { showConfirmModal } from './modal.js';

function closeAllDropdowns() {
    document.querySelectorAll('.session-menu-dropdown').forEach(d => d.classList.add('hidden'));
}

/**
 * Enable inline editing for a session title.
 */
function startInlineEdit(sessionElement, sessionId, currentTitle) {
    const titleDiv = sessionElement.querySelector('[data-action="load"] .font-bold');
    const originalText = titleDiv.innerText;

    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentTitle || '';
    input.className = 'w-full text-sm font-bold bg-surface-container-lowest border border-primary rounded px-2 py-1 outline-none focus:ring-2 focus:ring-primary/50';

    titleDiv.replaceWith(input);
    input.focus();
    input.select();

    const save = async () => {
        const newTitle = input.value.trim();
        if (!newTitle) {
            input.replaceWith(titleDiv);
            return;
        }
        if (newTitle === originalText) {
            input.replaceWith(titleDiv);
            return;
        }
        try {
            await apiService.renameSession(sessionId, newTitle);
            titleDiv.innerText = newTitle;
            showToast('Session renamed', 'success');
            await loadSidebarHistory();
        } catch (err) {
            showToast('Failed to rename: ' + err.message, 'error');
            input.replaceWith(titleDiv);
        }
    };

    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            save();
        } else if (e.key === 'Escape') {
            input.value = originalText;
            input.replaceWith(titleDiv);
        }
    });
}

export async function loadSidebarHistory() {
    try {
        const res = await apiService.getChatHistory();
        const sessions = res.data;
        elements.sidebarChatList.innerHTML = '';

        sessions.forEach(chat => {
            const container = document.createElement('div');
            container.className = 'relative group';

            const isActive = AppState.sessionId === chat.id;
            const activeClass = isActive ? 'bg-primary-container/30 border-l-4 border-primary' : 'hover:bg-surface-container-high/50';

            container.innerHTML = `
                <div class="flex items-center justify-between p-3 cursor-pointer transition-colors ${activeClass} session-item" data-session-id="${chat.id}">
                    <div class="flex-1 min-w-0" data-action="load">
                        <div class="font-bold text-xs text-on-surface truncate">${chat.title || 'Untitled'}</div>
                        <div class="flex items-center gap-2 mt-1">
                            <span class="text-[9px] text-on-surface-variant">${chat.date}</span>
                            <span class="text-[09px] font-bold px-2 py-0.5 rounded-full ${chat.status === 'Completed' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}">${chat.status}</span>
                        </div>
                    </div>
                    <div class="relative">
                        <button class="menu-btn p-1 hover:bg-surface-container-high rounded-full transition-colors" data-session-id="${chat.id}">
                            <span class="material-symbols-outlined text-on-surface-variant text-[20px]">more_vert</span>
                        </button>
                        <div class="session-menu-dropdown hidden absolute right-0 top-8 bg-surface-container-lowest rounded-lg shadow-lg border border-outline-variant/20 py-1 z-50 min-w-[120px]">
                            <div class="rename-action px-4 py-2 text-sm hover:bg-surface-container-high cursor-pointer flex items-center gap-2" data-session-id="${chat.id}">
                                <span class="material-symbols-outlined text-[18px]">edit</span> Rename
                            </div>
                            <div class="delete-action px-4 py-2 text-sm text-error hover:bg-error/5 cursor-pointer flex items-center gap-2" data-session-id="${chat.id}">
                                <span class="material-symbols-outlined text-[18px]">delete</span> Delete
                            </div>
                        </div>
                    </div>
                </div>
            `;

            const sessionDiv = container.querySelector('.session-item');
            const loadArea = container.querySelector('[data-action="load"]');
            loadArea.addEventListener('click', (e) => {
                e.stopPropagation();
                // Update URL and load the session
                updateURL(chat.id);
                loadSession(chat.id);
            });

            const menuBtn = container.querySelector('.menu-btn');
            const dropdown = container.querySelector('.session-menu-dropdown');
            menuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                closeAllDropdowns();
                dropdown.classList.toggle('hidden');
            });

            container.querySelector('.rename-action').addEventListener('click', (e) => {
                e.stopPropagation();
                dropdown.classList.add('hidden');
                startInlineEdit(sessionDiv, chat.id, chat.title);
            });

            container.querySelector('.delete-action').addEventListener('click', async (e) => {
                e.stopPropagation();
                dropdown.classList.add('hidden');

                const confirmed = await showConfirmModal({
                    title: 'Delete Session',
                    message: 'Are you sure you want to delete this session? This action cannot be undone.',
                    confirmText: 'Delete',
                    cancelText: 'Cancel',
                    type: 'danger'
                });

                if (!confirmed) return;

                try {
                    await apiService.deleteSession(chat.id);
                    if (AppState.sessionId === chat.id) {
                        showState(elements.stateUpload);
                        updateURL(null);
                        AppState.sessionId = null;
                    }
                    await loadSidebarHistory();
                    showToast('Session deleted', 'success');
                } catch (err) {
                    showToast('Failed to delete: ' + err.message, 'error');
                }
            });

            elements.sidebarChatList.appendChild(container);
        });
    } catch (error) {
        console.error("Failed to load sidebar history:", error);
        showToast('Could not load session history', 'error');
    }
}

/**
 * Global function to trigger loading a specific chat from the sidebar.
 */
export async function loadSession(sessionId) {
    const module = await import('../features/interview.js');
    module.loadSpecificChat(sessionId);
}

document.addEventListener('click', closeAllDropdowns);