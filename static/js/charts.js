// Charts initialization for 7-Day Velocity Bar Chart & Subject Distribution Donut
(function () {
    let sevenDayChartInstance = null;
    let subjectChartInstance = null;

    function isDarkMode() {
        return document.body.classList.contains('dark-mode');
    }

    function getThemeColors() {
        const dark = isDarkMode();
        return {
            text: dark ? '#C9C1B3' : '#5C555F',
            textBold: dark ? '#F3EEE3' : '#2D282E',
            grid: dark ? 'rgba(235, 225, 198, 0.08)' : 'rgba(45, 40, 46, 0.06)',
            surface: dark ? '#2B262F' : '#FCFAF6',
            barAccent: dark ? '#C496A1' : '#986470',
            barHover: dark ? '#D3A9B3' : '#86555F',
        };
    }

    // --- 1. 7-Day Velocity Bar Chart ---
    function initSevenDayChart() {
        const el = document.getElementById('sevenDayBarChart');
        if (!el || typeof Chart === 'undefined') return;

        const labels = JSON.parse(el.dataset.labels || '[]');
        const values = JSON.parse(el.dataset.values || '[]');
        const fullDates = JSON.parse(el.dataset.fullDates || '[]');
        const theme = getThemeColors();

        const ctx = el.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 220);
        gradient.addColorStop(0, theme.barAccent);
        gradient.addColorStop(1, isDarkMode() ? 'rgba(196, 150, 161, 0.2)' : 'rgba(196, 150, 161, 0.4)');

        sevenDayChartInstance = new Chart(el, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Study Minutes',
                    data: values,
                    backgroundColor: gradient,
                    hoverBackgroundColor: theme.barHover,
                    borderRadius: 8,
                    borderSkipped: false,
                    maxBarThickness: 36,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: isDarkMode() ? '#1F1B22' : '#2D282E',
                        titleColor: '#F3EEE3',
                        bodyColor: '#EBE1C6',
                        padding: 10,
                        cornerRadius: 8,
                        displayColors: false,
                        callbacks: {
                            title: (items) => {
                                const idx = items[0].dataIndex;
                                return fullDates[idx] || items[0].label;
                            },
                            label: (item) => {
                                const m = item.raw;
                                const h = Math.floor(m / 60);
                                const rem = m % 60;
                                let timeStr = `${m} min`;
                                if (h > 0) {
                                    timeStr = rem > 0 ? `${h}h ${rem}m (${m} mins)` : `${h} hr (${m} mins)`;
                                }
                                return `⏱️ ${timeStr}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: theme.text,
                            font: { family: 'Plus Jakarta Sans', weight: '600', size: 12 },
                        },
                        border: { display: false },
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: theme.grid },
                        ticks: {
                            color: theme.text,
                            font: { family: 'Plus Jakarta Sans', size: 11 },
                            callback: (v) => v + 'm',
                            maxTicksLimit: 5,
                        },
                        border: { display: false },
                    }
                }
            }
        });
    }

    // --- 2. Subject Distribution Donut Chart ---
    function initSubjectChart() {
        const el = document.getElementById('subjectChart');
        if (!el || typeof Chart === 'undefined') return;

        const labels = JSON.parse(el.dataset.labels || '[]');
        const values = JSON.parse(el.dataset.values || '[]');
        const colors = JSON.parse(el.dataset.colors || '[]');
        const emptyMsg = document.getElementById('chartEmpty');
        const centerText = document.getElementById('donutCenterText');

        if (!values.length || values.every(v => v === 0)) {
            el.style.display = 'none';
            if (centerText) centerText.style.display = 'none';
            if (emptyMsg) {
                emptyMsg.textContent = 'No sessions logged yet.';
                emptyMsg.hidden = false;
            }
            return;
        }

        const theme = getThemeColors();

        subjectChartInstance = new Chart(el, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 3,
                    borderColor: theme.surface,
                    hoverOffset: 6,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '72%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: isDarkMode() ? '#1F1B22' : '#2D282E',
                        titleColor: '#F3EEE3',
                        bodyColor: '#EBE1C6',
                        padding: 10,
                        cornerRadius: 8,
                        callbacks: {
                            label: (item) => {
                                const total = values.reduce((a, b) => a + b, 0);
                                const pct = total > 0 ? Math.round((item.raw / total) * 100) : 0;
                                return ` ${item.raw} session${item.raw === 1 ? '' : 's'} (${pct}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Theme update trigger
    window.updateChartTheme = function () {
        const theme = getThemeColors();

        if (sevenDayChartInstance) {
            const chart = sevenDayChartInstance;
            chart.options.scales.x.ticks.color = theme.text;
            chart.options.scales.y.ticks.color = theme.text;
            chart.options.scales.y.grid.color = theme.grid;

            const ctx = chart.ctx;
            const gradient = ctx.createLinearGradient(0, 0, 0, 220);
            gradient.addColorStop(0, theme.barAccent);
            gradient.addColorStop(1, isDarkMode() ? 'rgba(196, 150, 161, 0.2)' : 'rgba(196, 150, 161, 0.4)');

            chart.data.datasets[0].backgroundColor = gradient;
            chart.data.datasets[0].hoverBackgroundColor = theme.barHover;
            chart.update();
        }

        if (subjectChartInstance) {
            const chart = subjectChartInstance;
            chart.data.datasets[0].borderColor = theme.surface;
            chart.update();
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initSevenDayChart();
            initSubjectChart();
        });
    } else {
        initSevenDayChart();
        initSubjectChart();
    }
})();