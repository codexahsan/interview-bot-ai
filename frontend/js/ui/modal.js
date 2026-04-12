/**
 * Custom confirmation modal.
 * Returns a Promise that resolves to true if confirmed, false otherwise.
 */
export function showConfirmModal({ title = 'Confirm', message = '', confirmText = 'Confirm', cancelText = 'Cancel', type = 'primary' } = {}) {
    return new Promise((resolve) => {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-black/30 backdrop-blur-sm z-[100] flex items-center justify-center p-4';
        
        // Modal container
        const modal = document.createElement('div');
        modal.className = 'bg-surface-container-lowest rounded-2xl shadow-xl max-w-md w-full p-6 transform transition-all';
        
        // Type-based confirm button color
        const confirmBtnClass = type === 'danger' 
            ? 'bg-error hover:bg-error/90 text-white' 
            : 'bg-primary hover:bg-primary/90 text-white';
        
        modal.innerHTML = `
            <h3 class="text-lg font-bold text-on-surface mb-2">${title}</h3>
            <p class="text-on-surface-variant text-sm mb-6">${message}</p>
            <div class="flex justify-end gap-3">
                <button class="modal-cancel px-4 py-2 text-sm font-medium text-on-surface-variant hover:bg-surface-container-high rounded-lg transition-colors">${cancelText}</button>
                <button class="modal-confirm px-4 py-2 text-sm font-medium rounded-lg transition-colors ${confirmBtnClass}">${confirmText}</button>
            </div>
        `;
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        const cleanup = () => overlay.remove();
        
        modal.querySelector('.modal-cancel').addEventListener('click', () => {
            resolve(false);
            cleanup();
        });
        
        modal.querySelector('.modal-confirm').addEventListener('click', () => {
            resolve(true);
            cleanup();
        });
        
        // Click outside to cancel
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                resolve(false);
                cleanup();
            }
        });
        
        // Escape key
        const onKeydown = (e) => {
            if (e.key === 'Escape') {
                resolve(false);
                cleanup();
                document.removeEventListener('keydown', onKeydown);
            }
        };
        document.addEventListener('keydown', onKeydown);
    });
}