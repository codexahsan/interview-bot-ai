// frontend/js/api.js

const API_BASE_URL = "http://127.0.0.1:8000";

const handleResponse = async (response) => {
    const result = await response.json();
    if (!response.ok || !result.success) {
        throw new Error(result.message || `HTTP Error: ${response.status}`);
    }
    return result;
};

export const apiService = {
    async uploadResume(file) {
        const formData = new FormData();
        formData.append("file", file);
        const response = await fetch(`${API_BASE_URL}/resume/upload`, { method: "POST", body: formData });
        return handleResponse(response);
    },

    async createChatSession(resumeId) {
        const response = await fetch(`${API_BASE_URL}/chat/new/${resumeId}`, { method: "POST" });
        return handleResponse(response);
    },

    async startInterview(sessionId) {
        const response = await fetch(`${API_BASE_URL}/interview/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId })
        });
        return handleResponse(response);
    },

    async submitAnswer(sessionId, answerText) {
        const response = await fetch(`${API_BASE_URL}/interview/answer`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, answer: answerText })
        });
        return handleResponse(response);
    },

    async getChatHistory() {
        const response = await fetch(`${API_BASE_URL}/interview/history`, { method: "GET" });
        return handleResponse(response);
    },

    async getSessionDetails(sessionId) {
        const response = await fetch(`${API_BASE_URL}/interview/session/${sessionId}`, { method: "GET" });
        return handleResponse(response);
    },

    async renameSession(sessionId, newTitle) {
        const response = await fetch(`${API_BASE_URL}/interview/session/${sessionId}/rename`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ new_title: newTitle })
        });
        return handleResponse(response);
    },

    async deleteSession(sessionId) {
        const response = await fetch(`${API_BASE_URL}/interview/session/${sessionId}`, { method: "DELETE" });
        return handleResponse(response);
    },

    async finalizeInterview(sessionId) {
        const response = await fetch(`${API_BASE_URL}/interview/end`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId })
        });
        return handleResponse(response);
    },

    // ✅ Coaching endpoints
    async startCoachingSession(interviewSessionId) {
        const response = await fetch(`${API_BASE_URL}/coach/start/${interviewSessionId}`, {
            method: 'POST'
        });
        return handleResponse(response);
    },

    async sendCoachingMessage(sessionId, message) {
        const response = await fetch(`${API_BASE_URL}/coach/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, message: message })
        });
        return handleResponse(response);
    }
};