// frontend/js/ui/domElements.js

/**
 * Cached DOM element references.
 */
export const elements = {
    // State views
    stateUpload: document.getElementById('state-upload'),
    stateProcessing: document.getElementById('state-processing'),
    stateSummary: document.getElementById('state-summary'),
    stateInterview: document.getElementById('state-interview'),

    // Upload
    uploadZone: document.getElementById('upload-zone'),
    resumeInput: document.getElementById('resume-upload'),
    selectFileBtn: document.getElementById('select-file-btn'),

    // Buttons
    newInterviewBtn: document.getElementById('new-interview-btn'),
    startInterviewBtn: document.getElementById('start-interview-btn'),
    endSessionBtn: document.getElementById('end-session-btn'),
    submitAnswerBtn: document.getElementById('submit-answer-btn'),

    // Interview UI
    answerInput: document.getElementById('answer-input'),
    questionProgressText: document.getElementById('question-progress-text'),
    questionProgressBar: document.getElementById('question-progress-bar'),
    conversationContainer: document.getElementById('conversation-container'),
    answerInputBox: document.getElementById('answer-input-box'),
    scrollContainer: document.getElementById('conversation-scroll-container'),

    // Sidebar
    sidebarChatList: document.getElementById('sidebar-chat-list'),
    sidebar: document.getElementById('sidebar'),
    sidebarOverlay: document.getElementById('sidebar-overlay'),
    mobileMenuBtn: document.getElementById('mobile-menu-btn'),

    // Coaching
    stateCoaching: document.getElementById('state-coaching'),
    coachingScrollContainer: document.getElementById('coaching-scroll-container'),
    coachingConversationContainer: document.getElementById('coaching-conversation-container'),
    coachingMessageInput: document.getElementById('coaching-message-input'),
    sendCoachingMessageBtn: document.getElementById('send-coaching-message-btn'),
    endCoachingBtn: document.getElementById('end-coaching-btn'),
};