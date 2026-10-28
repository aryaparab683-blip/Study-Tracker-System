// Pomodoro Focus Timer with SVG Ring Animation & Audio Chime
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

    const modePills = {
        focus: document.getElementById('modeFocus'),
        short: document.getElementById('modeShort'),
        long: document.getElementById('modeLong'),
    };

    const baseTitle = document.title;
    let state = load();

    function fresh(modeKey = 'focus') {
        const mode = MODES[modeKey] ? modeKey : 'focus';
        return {
            mode: mode,
            running: false,
            remaining: MODES[mode].duration,
            total: MODES[mode].duration,
            endsAt: 0,
            cycle: 1,
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
        // Stroke dashoffset: 0 is full circle, CIRCUMFERENCE is empty
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

    function onComplete() {
        playChime();
        if (window.Notification && Notification.permission === 'granted') {
            const title = state.mode === 'focus' ? '🎯 Focus Session Complete!' : '⏰ Break Over!';
            const body = state.mode === 'focus' ? 'Great work! Take a 5-minute break.' : 'Time to dive back into deep focus.';
            new Notification(title, { body });
        }

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
        save();
        render();
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
        state.endsAt = Date.now() + state.remaining * 1000;
        state.running = true;
        save();
        render();
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
    }

    function setMode(modeKey) {
        if (!MODES[modeKey]) return;
        state.mode = modeKey;
        state.total = MODES[modeKey].duration;
        state.remaining = state.total;
        state.running = false;
        state.endsAt = 0;
        save();
        render();
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