// frontend/js/core/state.js

/**
 * Global application state.
 */
export const AppState = {
    currentView: 'upload',
    resumeId: null,
    sessionId: null,
    currentQuestionNum: 1,
    isUploading: false,
    processingTimeout: null,
};

export const TOTAL_QUESTIONS = 5;