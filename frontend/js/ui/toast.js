// frontend/js/ui/toast.js

/**
 * Simple toast notification system.
 * Displays messages in the top-right corner with auto-dismiss.
 */

let toastContainer = null;

function createToastContainer() {
    if (toastContainer) return toastContainer;
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'fixed top-4 right-4 z-[100] flex flex-col gap-2';
    document.body.appendChild(toastContainer);
    return toastContainer;
}

/**
 * Show a toast message.
 * @param {string} message - The message to display.
 * @param {'success'|'error'|'info'|'warning'} type - Toast type.
 * @param {number} duration - Duration in ms before auto-dismiss (default 4000).
 */
export function showToast(message, type = 'info', duration = 4000) {
    const container = createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast flex items-start gap-3 p-4 rounded-xl shadow-lg border text-sm max-w-sm transform transition-all duration-300 animate-slide-in`;
    
    // Type-specific styling
    const typeClasses = {
        success: 'bg-green-50 border-green-200 text-green-800',
        error: 'bg-red-50 border-red-200 text-red-800',
        warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
        info: 'bg-blue-50 border-blue-200 text-blue-800',
    };
    toast.classList.add(...typeClasses[type].split(' '));
    
    // Icon based on type
    const icons = {
        success: 'check_circle',
        error: 'error',
        warning: 'warning',
        info: 'info',
    };
    
    toast.innerHTML = `
        <span class="material-symbols-outlined text-[20px] shrink-0">${icons[type]}</span>
        <span class="flex-1">${message}</span>
        <button class="toast-close shrink-0 hover:opacity-70 transition-opacity">
            <span class="material-symbols-outlined text-[18px]">close</span>
        </button>
    `;
    
    // Close button functionality
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => dismissToast(toast));
    
    // Auto-dismiss
    const timeout = setTimeout(() => dismissToast(toast), duration);
    toast.dataset.timeout = timeout;
    
    container.appendChild(toast);
}

function dismissToast(toast) {
    clearTimeout(Number(toast.dataset.timeout));
    toast.classList.add('opacity-0', 'translate-x-full');
    setTimeout(() => toast.remove(), 300);
}

// Add animation CSS dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes slide-in {
        from { opacity: 0; transform: translateX(100%); }
        to { opacity: 1; transform: translateX(0); }
    }
    .animate-slide-in {
        animation: slide-in 0.3s ease-out;
    }
`;
document.head.appendChild(style);