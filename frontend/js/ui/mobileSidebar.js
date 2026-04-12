// frontend/js/ui/mobileSidebar.js 

import { elements } from './domElements.js';

export function initMobileSidebar() {
    const { sidebar, sidebarOverlay, mobileMenuBtn } = elements;

    function openSidebar() {
        sidebar.classList.remove('-translate-x-full');
        sidebar.classList.add('translate-x-0');
        sidebarOverlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar.classList.add('-translate-x-full');
        sidebar.classList.remove('translate-x-0');
        sidebarOverlay.classList.add('hidden');
        document.body.style.overflow = '';
    }

    mobileMenuBtn?.addEventListener('click', openSidebar);
    sidebarOverlay?.addEventListener('click', closeSidebar);

    window.addEventListener('resize', () => {
        if (window.innerWidth >= 1024) {
            closeSidebar();
        }
    });
}
