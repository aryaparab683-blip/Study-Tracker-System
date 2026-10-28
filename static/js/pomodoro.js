// Pomodoro Focus Timer with SVG Ring Animation, Audio Chime & Backend Persistence
// State lives in localStorage with absolute end timestamp for background tab navigation.
(function () {
    const KEY = 'study-tracker-pomodoro-v2';
    const MODES = {
        focus: { name: 'FOCUS', duration: 25 * 60, cycleLabel: 'Focus Block' },
        short: { name: 'SHORT BREAK', duration: 5 * 60, cycleLabel: 'Short Break' },
        long: { name: 'LONG BREAK', duration: 15 * 60, cycleLabel: 'Long Break' },
    };
    const CIRCUMFERENCE = 578.05; // 2 * Math.PI * 92

    const display = document.getElementById('timerDisplay');
    const modeLabel = document.getElementById('timerMode');
    const cycleLabel = document.getElementById('timerCycle');
    const startBtn = document.getElementById('startBtn');
    const pauseBtn = document.getElementById('pauseBtn');
    const resetBtn = document.getElementById('resetBtn');
    const ringProgress = document.getElementById('timerRingProgress');
    const sidebarText = document.getElementById('sidebarTimerText');
    const sidebarBadge = document.getElementById('sidebarTimerBadge');
    const subjectSelect = document.getElementById('timerSubject');
    const feedbackEl = document.getElementById('timerFeedback');

    const modePills = {
        focus: document.getElementById('modeFocus'),
        short: document.getElementById('modeShort'),
        long: document.getElementById('modeLong'),
    };

    const baseTitle = document.title;
    let state = load();
    let isSaving = false;
    let feedbackTimer = null;

    // Sync subject select with saved state if available
    if (subjectSelect && state.subjectId) {
        subjectSelect.value = state.subjectId;
    }
    if (subjectSelect) {
        subjectSelect.addEventListener('change', () => {
            state.subjectId = subjectSelect.value;
            save();
        });
    }

    function fresh(modeKey = 'focus') {
        const mode = MODES[modeKey] ? modeKey : 'focus';
        return {
            mode: mode,
            running: false,
            remaining: MODES[mode].duration,
            total: MODES[mode].duration,
            endsAt: 0,
            cycle: 1,
            token: null,
            subjectId: subjectSelect ? subjectSelect.value : '',
        };
    }

    function load() {
        try {
            const raw = JSON.parse(localStorage.getItem(KEY));
            if (raw && MODES[raw.mode] && typeof raw.remaining === 'number' && typeof raw.total === 'number') {
                return raw;
            }
        } catch (e) { /* ignore */ }
        return fresh();
    }

    function save() {
        try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* ignore */ }
    }

    function playChime() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const now = ctx.currentTime;

            // Harmonious chime chords (D5, F#5, A5)
            const freqs = [587.33, 739.99, 880.00];
            freqs.forEach((freq, idx) => {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, now + idx * 0.08);

                gain.gain.setValueAtTime(0.001, now + idx * 0.08);
                gain.gain.exponentialRampToValueAtTime(0.25, now + idx * 0.08 + 0.05);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.08 + 1.2);

                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(now + idx * 0.08);
                osc.stop(now + idx * 0.08 + 1.3);
            });
        } catch (e) {
            // Audio context blocked or unsupported
        }
    }

    function fmt(totalSec) {
        const m = Math.floor(totalSec / 60).toString().padStart(2, '0');
        const s = (totalSec % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    }

    function secondsLeft() {
        if (!state.running) return state.remaining;
        return Math.max(0, Math.ceil((state.endsAt - Date.now()) / 1000));
    }

    function updateRing(left) {
        if (!ringProgress) return;
        const total = state.total || MODES[state.mode].duration;
        const progress = Math.max(0, Math.min(1, left / total));
        const offset = CIRCUMFERENCE * (1 - progress);
        ringProgress.style.strokeDashoffset = offset;
    }

    function render() {
        const left = secondsLeft();
        const formatted = fmt(left);
        const modeInfo = MODES[state.mode] || MODES.focus;

        if (display) display.textContent = formatted;
        if (modeLabel) modeLabel.textContent = modeInfo.name;
        if (cycleLabel) {
            cycleLabel.textContent = state.mode === 'focus' ? `Session ${state.cycle} of 4` : modeInfo.cycleLabel;
        }

        if (startBtn) startBtn.disabled = state.running;
        if (pauseBtn) pauseBtn.disabled = !state.running;

        // Highlight mode pills
        Object.keys(modePills).forEach(k => {
            const pill = modePills[k];
            if (pill) {
                pill.classList.toggle('active', state.mode === k);
            }
        });

        // Update SVG Ring
        updateRing(left);

        // Sidebar quick badge
        if (sidebarText) {
            if (state.running) {
                sidebarText.textContent = `${state.mode === 'focus' ? 'Focus' : 'Break'} (${formatted})`;
                if (sidebarBadge) sidebarBadge.classList.add('active-timer');
            } else {
                sidebarText.textContent = left < (state.total || 1500) ? `Paused (${formatted})` : 'Pomodoro Ready';
                if (sidebarBadge) sidebarBadge.classList.remove('active-timer');
            }
        }

        // Browser Tab Title
        if (state.running) {
            document.title = `${formatted} ${modeInfo.name} · ${baseTitle}`;
        } else {
            document.title = baseTitle;
        }
    }

    function showFeedback(msg, type = 'info', options = {}) {
        if (!feedbackEl) return;
        if (feedbackTimer) clearTimeout(feedbackTimer);

        feedbackEl.className = `timer-feedback-pill ${type}`;
        feedbackEl.hidden = false;
        feedbackEl.innerHTML = '';

        const textSpan = document.createElement('span');
        textSpan.textContent = msg;
        feedbackEl.appendChild(textSpan);

        if (options.retry) {
            const retryBtn = document.createElement('button');
            retryBtn.type = 'button';
            retryBtn.className = 'btn-retry';
            retryBtn.textContent = 'Retry';
            retryBtn.addEventListener('click', (e) => {
                e.preventDefault();
                options.retry();
            });
            feedbackEl.appendChild(retryBtn);
        } else if (type === 'success') {
            feedbackTimer = setTimeout(() => {
                hideFeedback();
            }, 6000);
        }
    }

    function hideFeedback() {
        if (!feedbackEl) return;
        feedbackEl.hidden = true;
        feedbackEl.innerHTML = '';
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function updateDashboardUI(data) {
        if (!data || !data.stats) return;

        const weekMin = document.getElementById('metricWeekMinutes');
        if (weekMin) weekMin.innerHTML = `${data.stats.week_minutes} <span class="metric-unit">min</span>`;

        const weekHrs = document.getElementById('metricWeekHours');
        if (weekHrs) weekHrs.textContent = `${data.stats.week_hours} hrs`;

        const streak = document.getElementById('metricStreak');
        if (streak) streak.innerHTML = `${data.stats.streak} <span class="metric-unit">day${data.stats.streak === 1 ? '' : 's'}</span>`;

        const totalSessions = document.getElementById('metricTotalSessions');
        if (totalSessions) totalSessions.innerHTML = `${data.stats.total_sessions} <span class="metric-unit">sessions</span>`;

        const totalHrs = document.getElementById('metricTotalHours');
        if (totalHrs) totalHrs.textContent = `${data.stats.total_hours} hrs`;

        const sessionList = document.getElementById('dashSessionList');
        if (sessionList && data.session) {
            const emptyBox = sessionList.querySelector('.empty-box');
            if (emptyBox) emptyBox.remove();

            const item = document.createElement('div');
            item.className = 'dash-session-item';
            item.innerHTML = `
                <div class="session-main">
                    <strong class="session-title">${escapeHtml(data.session.title)}</strong>
                    <div class="session-meta">
                        <span class="subject-pill" style="--dot: ${escapeHtml(data.session.subject_color)};">${escapeHtml(data.session.subject_name)}</span>
                        <span class="session-date">${escapeHtml(data.session.date)}</span>
                    </div>
                </div>
                <div class="session-duration-badge">${Number(data.session.duration)}m</div>
            `;
            sessionList.prepend(item);
        }
    }

    function saveFocusSession(token, duration, subjectId) {
        if (isSaving) return;
        isSaving = true;

        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

        const formData = new URLSearchParams();
        formData.append('token', token);
        formData.append('duration', duration);
        if (subjectId) {
            formData.append('subject_id', subjectId);
        }
        if (csrfToken) {
            formData.append('csrf_token', csrfToken);
        }

        showFeedback('Saving focus session to your study log...', 'info');

        fetch('/api/pomodoro/log', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken,
            },
            body: formData.toString(),
        })
        .then(res => {
            isSaving = false;
            return res.json().then(data => {
                if (!res.ok) {
                    throw new Error(data.error || 'Server error');
                }
                return data;
            });
        })
        .then(data => {
            if (data.status === 'already_logged') {
                showFeedback('Focus session already recorded.', 'info');
            } else {
                showFeedback(`🎯 Focus session recorded (${duration} min)!`, 'success');
                updateDashboardUI(data);
            }
        })
        .catch(err => {
            isSaving = false;
            showFeedback(`⚠️ Could not save focus session (${err.message}).`, 'error', {
                retry: () => saveFocusSession(token, duration, subjectId)
            });
        });
    }

    function onComplete() {
        playChime();
        if (window.Notification && Notification.permission === 'granted') {
            const title = state.mode === 'focus' ? '🎯 Focus Session Complete!' : '⏰ Break Over!';
            const body = state.mode === 'focus' ? 'Great work! Take a 5-minute break.' : 'Time to dive back into deep focus.';
            new Notification(title, { body });
        }

        const wasFocus = state.mode === 'focus';
        const completedToken = state.token;
        const completedDuration = Math.round((state.total || 1500) / 60);
        const completedSubjectId = state.subjectId || (subjectSelect ? subjectSelect.value : '');

        // Advance phase automatically
        if (state.mode === 'focus') {
            state.cycle = (state.cycle % 4) + 1;
            const nextMode = state.cycle === 1 ? 'long' : 'short';
            state.mode = nextMode;
            state.total = MODES[nextMode].duration;
            state.remaining = state.total;
        } else {
            state.mode = 'focus';
            state.total = MODES.focus.duration;
            state.remaining = state.total;
        }
        state.running = false;
        state.endsAt = 0;
        state.token = null;
        save();
        render();

        // Persist to backend if it was a focus session
        if (wasFocus && completedToken) {
            saveFocusSession(completedToken, completedDuration, completedSubjectId);
        }
    }

    function tick() {
        if (state.running) {
            if (Date.now() >= state.endsAt) {
                onComplete();
            } else {
                render();
            }
        }
    }

    function start() {
        if (state.running) return;
        if (window.Notification && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        if (state.mode === 'focus' && !state.token) {
            state.token = 'pomo_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
        }
        if (subjectSelect) {
            state.subjectId = subjectSelect.value || '';
        }
        state.endsAt = Date.now() + state.remaining * 1000;
        state.running = true;
        save();
        render();
        hideFeedback();
    }

    function pause() {
        if (!state.running) return;
        state.remaining = secondsLeft();
        state.running = false;
        state.endsAt = 0;
        save();
        render();
    }

    function reset() {
        state = fresh(state.mode);
        save();
        render();
        hideFeedback();
    }

    function setMode(modeKey) {
        if (!MODES[modeKey]) return;
        state.mode = modeKey;
        state.total = MODES[modeKey].duration;
        state.remaining = state.total;
        state.running = false;
        state.endsAt = 0;
        state.token = null;
        save();
        render();
        hideFeedback();
    }

    // Attach Event Listeners
    if (startBtn) startBtn.addEventListener('click', start);
    if (pauseBtn) pauseBtn.addEventListener('click', pause);
    if (resetBtn) resetBtn.addEventListener('click', reset);

    Object.keys(modePills).forEach(k => {
        const pill = modePills[k];
        if (pill) {
            pill.addEventListener('click', () => setMode(k));
        }
    });

    setInterval(tick, 500);
    render();
})();
