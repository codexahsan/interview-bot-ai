// frontend/js/features/upload.js

import { apiService } from '../api.js';
import { AppState } from '../core/state.js';
import { elements } from '../ui/domElements.js';
import { showState, updateURL } from '../ui/stateManager.js';
import { loadSidebarHistory } from '../ui/sidebar.js';
import { showToast } from '../ui/toast.js';

// Allowed file types and max size (5MB)
const ALLOWED_TYPES = ['application/pdf'];
const MAX_SIZE = 5 * 1024 * 1024; // 5MB

function validateFile(file) {
    if (!ALLOWED_TYPES.includes(file.type)) {
        showToast('Only PDF files are allowed.', 'error');
        return false;
    }
    if (file.size > MAX_SIZE) {
        showToast('File size must be less than 5MB.', 'error');
        return false;
    }
    return true;
}

export async function handleFileUpload(file) {
    if (!file || AppState.isUploading) return;
    if (!validateFile(file)) {
        elements.resumeInput.value = ''; // clear invalid file
        return;
    }

    AppState.isUploading = true;

    try {
        showState(elements.stateProcessing);

        const uploadRes = await apiService.uploadResume(file);
        AppState.resumeId = uploadRes.data.resume_id;

        const sessionRes = await apiService.createChatSession(AppState.resumeId);
        AppState.sessionId = sessionRes.data.id;
        updateURL(AppState.sessionId);

        showState(elements.stateSummary);
        await loadSidebarHistory();
    } catch (error) {
        showToast("Upload failed: " + error.message, 'error');
        showState(elements.stateUpload);
    } finally {
        AppState.isUploading = false;
        elements.resumeInput.value = '';
    }
}

export function initUploadListeners() {
    const { uploadZone, resumeInput, selectFileBtn } = elements;

    uploadZone.addEventListener('click', () => resumeInput.click());
    selectFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resumeInput.click();
    });

    resumeInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleFileUpload(file);
    });

    // Drag & Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.body.addEventListener(eventName, e => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    uploadZone.addEventListener('dragover', () => {
        uploadZone.classList.add('border-primary', 'bg-primary-fixed/40');
    });
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('border-primary', 'bg-primary-fixed/40');
    });
    uploadZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            Object.defineProperty(resumeInput, 'files', { value: files });
            resumeInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
}