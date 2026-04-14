// frontend/js/app.js

import { elements } from './ui/domElements.js';
import { showState, clearConversation, unlockChat, updateURL } from './ui/stateManager.js';
import { loadSidebarHistory, loadSession } from './ui/sidebar.js';
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
    updateURL(null);
    clearConversation();
    unlockChat();
    showState(elements.stateUpload);
});

// Initialize everything
async function init() {
    initMobileSidebar();
    initUploadListeners();
    initInterviewListeners();
await loadSidebarHistory();

    // REFRESH LOGIC: Check if session exists in URL
    if (AppState.sessionId) {
        console.log("Restoring session:", AppState.sessionId);
        // loadSession wahi function hai jo sidebar click par chalta hai
        loadSession(AppState.sessionId);
    } else {
        showState(elements.stateUpload);
    }
}

document.addEventListener('DOMContentLoaded', init);