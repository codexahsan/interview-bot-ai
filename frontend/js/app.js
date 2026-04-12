// frontend/js/app.js

import { elements } from './ui/domElements.js';
import { showState, clearConversation, unlockChat } from './ui/stateManager.js';
import { loadSidebarHistory } from './ui/sidebar.js';
import { initMobileSidebar } from './ui/mobileSidebar.js';
import { initUploadListeners } from './features/upload.js';
import { initInterviewListeners } from './features/interview.js';
import { AppState } from './core/state.js';

// New Interview button resets everything
elements.newInterviewBtn.addEventListener('click', () => {
    if (AppState.processingTimeout) clearTimeout(AppState.processingTimeout);
    AppState.sessionId = null;
    AppState.currentQuestionNum = 1;
    AppState.isUploading = false;
    clearConversation();
    unlockChat();
    showState(elements.stateUpload);
});

// Initialize everything
function init() {
    initMobileSidebar();
    initUploadListeners();
    initInterviewListeners();

    showState(elements.stateUpload);
    loadSidebarHistory();
}

document.addEventListener('DOMContentLoaded', init);