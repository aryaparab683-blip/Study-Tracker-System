// Main Application Scripts: Theme, Mobile Sidebar Drawer, Heatmap Tooltips, and Form Helpers

// --- 1. Dark/Light Theme Management ---
function readTheme() {
    try { return localStorage.getItem('study-theme') || 'light'; } catch (e) { return 'light'; }
}

function saveTheme(mode) {
    try { localStorage.setItem('study-theme', mode); } catch (e) { /* ignore */ }
}

function updateTheme(mode) {
    const dark = mode === 'dark';
    document.body.classList.toggle('dark-mode', dark);
    document.body.classList.toggle('light-mode', !dark);

    // Update theme toggle buttons
    document.querySelectorAll('#themeToggle, .theme-toggle-btn').forEach(btn => {
        btn.setAttribute('aria-pressed', String(dark));
    });

    if (window.updateChartTheme) {
        window.updateChartTheme();
    }
}

// Initialize theme immediately
updateTheme(readTheme());

document.addEventListener('DOMContentLoaded', () => {
    // Theme toggle listeners
    document.querySelectorAll('#themeToggle, .theme-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const next = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
            updateTheme(next);
            saveTheme(next);
        });
    });

    // --- 2. Mobile Sidebar Drawer Toggle ---
    const sidebar = document.getElementById('appSidebar');
    const toggleBtn = document.getElementById('sidebarToggleBtn');
    const closeBtn = document.getElementById('sidebarCloseBtn');
    const backdrop = document.getElementById('sidebarBackdrop');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('open');
        if (backdrop) backdrop.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (backdrop) backdrop.classList.remove('show');
        document.body.style.overflow = '';
    }

    if (toggleBtn) toggleBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (backdrop) backdrop.addEventListener('click', closeSidebar);

    // Close sidebar on ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
            closeSidebar();
        }
    });

    // --- 3. Heatmap Matrix Tooltip Interactions ---
    const tooltip = document.getElementById('heatmapTooltip');
    const cells = document.querySelectorAll('.heatmap-cell');

    if (tooltip && cells.length > 0) {
        cells.forEach(cell => {
            cell.addEventListener('mouseenter', (e) => {
                const dateLabel = cell.dataset.label;
                const minutes = parseInt(cell.dataset.minutes || '0', 10);
                const count = parseInt(cell.dataset.count || '0', 10);
                const isFuture = cell.classList.contains('is-future');

                let content = '';
                if (isFuture) {
                    content = `<strong>${dateLabel}</strong><span>Future date</span>`;
                } else if (minutes === 0) {
                    content = `<strong>${dateLabel}</strong><span>No activity logged</span>`;
                } else {
                    const h = Math.floor(minutes / 60);
                    const rem = minutes % 60;
                    const durationStr = h > 0 ? (rem > 0 ? `${h}h ${rem}m` : `${h}h`) : `${minutes}m`;
                    content = `<strong>${dateLabel}</strong><span>${durationStr} focused · ${count} session${count === 1 ? '' : 's'}</span>`;
                }

                tooltip.innerHTML = content;
                tooltip.hidden = false;

                const rect = cell.getBoundingClientRect();
                const scrollX = window.scrollX || window.pageXOffset;
                const scrollY = window.scrollY || window.pageYOffset;

                // Position centered above the cell
                const tooltipWidth = 170;
                let left = rect.left + scrollX + (rect.width / 2) - (tooltipWidth / 2);
                let top = rect.top + scrollY - 48;

                // Viewport boundaries
                left = Math.max(10, Math.min(window.innerWidth - tooltipWidth - 10, left));

                tooltip.style.left = `${left}px`;
                tooltip.style.top = `${top}px`;
            });

            cell.addEventListener('mouseleave', () => {
                tooltip.hidden = true;
            });

            cell.addEventListener('focus', () => {
                cell.dispatchEvent(new MouseEvent('mouseenter'));
            });

            cell.addEventListener('blur', () => {
                tooltip.hidden = true;
            });
        });
    }

    // --- 4. Auto-dismiss Flash Alerts ---
    setTimeout(() => {
        document.querySelectorAll('.flash-alert:not(.error)').forEach(alert => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-6px)';
            setTimeout(() => alert.remove(), 400);
        });
    }, 6000);
});

// --- 5. Form Helpers: Password Toggle ---
window.togglePasswordVisibility = function (inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';

    // Toggle icon state
    if (btn) {
        btn.classList.toggle('active', isPassword);
        btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
    }
};