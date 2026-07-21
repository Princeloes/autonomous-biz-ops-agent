document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const runBtn = document.getElementById('run-agent-btn');
    const instructionInput = document.getElementById('agent-instruction');
    const planSteps = document.getElementById('plan-steps');
    const consoleLogs = document.getElementById('console-logs');
    const connectionStatus = document.getElementById('connection-status');
    const modeStatus = document.getElementById('mode-status');
    const newMemoryInput = document.getElementById('new-memory-input');
    const addMemoryBtn = document.getElementById('add-memory-btn');
    const memoryList = document.getElementById('memory-list');
    const emailList = document.getElementById('email-list');
    const calendarList = document.getElementById('calendar-list');
    const reportsList = document.getElementById('reports-list');
    const reportModal = document.getElementById('report-modal');
    const modalTitle = document.getElementById('modal-report-title');
    const modalBody = document.getElementById('modal-report-body');
    const closeModal = document.querySelector('.close-modal');

    // Tab Navigation
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const targetTab = btn.getAttribute('data-tab');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // Close Modal Event
    closeModal.addEventListener('click', () => {
        reportModal.classList.add('hidden');
    });

    window.addEventListener('click', (e) => {
        if (e.target === reportModal) {
            reportModal.classList.add('hidden');
        }
    });

    // Logger Utility
    function log(message, type = 'system') {
        const span = document.createElement('span');
        span.className = `log-line ${type}-log`;
        span.innerText = `[${new Date().toLocaleTimeString()}] ${message}`;
        consoleLogs.appendChild(span);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    // Load Configuration
    async function loadConfig() {
        try {
            const res = await fetch('/api/config');
            const config = await res.json();
            
            connectionStatus.classList.remove('offline');
            connectionStatus.classList.add('online');
            connectionStatus.innerHTML = '<span class="indicator"></span> Online';
            
            if (config.is_mock_mode) {
                modeStatus.innerText = 'Mock Mode (Local Simulation)';
                modeStatus.style.borderColor = 'rgba(245, 158, 11, 0.3)';
                modeStatus.style.color = 'var(--warning)';
                modeStatus.style.background = 'rgba(245, 158, 11, 0.05)';
            } else {
                modeStatus.innerText = `Live Mode (${config.model_name})`;
                modeStatus.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                modeStatus.style.color = 'var(--success)';
                modeStatus.style.background = 'rgba(16, 185, 129, 0.05)';
            }
        } catch (err) {
            connectionStatus.classList.remove('online');
            connectionStatus.classList.add('offline');
            connectionStatus.innerHTML = '<span class="indicator"></span> Disconnected';
            log('Failed to connect to backend server API.', 'error');
        }
    }

    // Refresh Data Hubs (Mail, Calendar, Memory, Reports)
    async function refreshData() {
        try {
            // Load Emails
            const emailsRes = await fetch('/api/mailbox');
            const emails = await emailsRes.json();
            emailList.innerHTML = '';
            if (emails.length === 0) {
                emailList.innerHTML = '<div class="empty-state">No emails in mailbox.</div>';
            } else {
                emails.forEach(email => {
                    const isUnread = email.status === 'unread';
                    const isSent = email.status === 'sent';
                    const emailCard = document.createElement('div');
                    emailCard.className = 'card-item';
                    emailCard.innerHTML = `
                        <div class="email-meta">
                            <span>From: ${email.from}</span>
                            <span>${email.date}</span>
                        </div>
                        <div class="email-subject">
                            ${isUnread ? '<span class="unread-badge"></span>' : ''}
                            ${email.subject}
                            ${isSent ? '<span style="font-size: 0.7rem; opacity: 0.6; margin-left: auto;">(Sent)</span>' : ''}
                        </div>
                        <div class="email-body">${email.body}</div>
                    `;
                    emailList.appendChild(emailCard);
                });
            }

            // Load Calendar Events
            const calRes = await fetch('/api/calendar');
            const events = await calRes.json();
            calendarList.innerHTML = '';
            if (events.length === 0) {
                calendarList.innerHTML = '<div class="empty-state">No events scheduled.</div>';
            } else {
                events.forEach(event => {
                    const eventCard = document.createElement('div');
                    eventCard.className = 'card-item';
                    eventCard.innerHTML = `
                        <div class="calendar-time">${event.start} - ${event.end}</div>
                        <div class="calendar-title">${event.title}</div>
                        <div class="calendar-desc">${event.description}</div>
                    `;
                    calendarList.appendChild(eventCard);
                });
            }

            // Load Memories
            const memRes = await fetch('/api/memories');
            const memories = await memRes.json();
            memoryList.innerHTML = '';
            if (memories.length === 0) {
                memoryList.innerHTML = '<div class="empty-state">No memories stored.</div>';
            } else {
                memories.forEach(mem => {
                    const memCard = document.createElement('div');
                    memCard.className = 'card-item memory-item';
                    memCard.innerHTML = `
                        <span class="memory-text">${mem.text}</span>
                        <button class="delete-btn" data-id="${mem.id}"><i class="fas fa-trash"></i></button>
                    `;
                    memCard.querySelector('.delete-btn').addEventListener('click', () => deleteMemory(mem.id));
                    memoryList.appendChild(memCard);
                });
            }

            // Load Reports
            const repRes = await fetch('/api/reports');
            const reports = await repRes.json();
            reportsList.innerHTML = '';
            if (reports.length === 0) {
                reportsList.innerHTML = '<div class="empty-state">No reports generated yet.</div>';
            } else {
                reports.forEach(report => {
                    const repCard = document.createElement('div');
                    repCard.className = 'card-item report-item';
                    repCard.innerHTML = `
                        <div class="report-header">
                            <span class="report-title">${report.filename}</span>
                        </div>
                    `;
                    repCard.addEventListener('click', () => showReportModal(report.filename, report.content));
                    reportsList.appendChild(repCard);
                });
            }

        } catch (err) {
            console.error('Error refreshing dashboard data:', err);
        }
    }

    // Show Report Modal
    function showReportModal(title, rawContent) {
        modalTitle.innerText = title;
        // Simple basic markdown renderer for display
        let formatted = rawContent
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^\*\*(.*)\*\*/gim, '<strong>$1</strong>')
            .replace(/^\*(.*)\*/gim, '<em>$1</em>')
            .replace(/\n/g, '<br>');
        
        modalBody.innerHTML = formatted;
        reportModal.classList.remove('hidden');
    }

    // Add Memory
    async function addMemory() {
        const text = newMemoryInput.value.trim();
        if (!text) return;
        
        try {
            const res = await fetch('/api/memories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            if (res.ok) {
                newMemoryInput.value = '';
                log(`Added new memory: "${text}"`, 'system');
                await refreshData();
            }
        } catch (err) {
            log('Failed to add memory.', 'error');
        }
    }

    // Delete Memory
    async function deleteMemory(id) {
        try {
            const res = await fetch(`/api/memories/${id}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                log('Deleted memory record.', 'system');
                await refreshData();
            }
        } catch (err) {
            log('Failed to delete memory.', 'error');
        }
    }

    // Run Agent
    async function runAgentMission() {
        const prompt = instructionInput.value.trim();
        if (!prompt) return;

        // Reset UI
        planSteps.innerHTML = '';
        consoleLogs.innerHTML = '';
        runBtn.disabled = true;
        runBtn.querySelector('.btn-text').innerText = 'Running Mission...';
        runBtn.querySelector('.loader').classList.remove('hidden');

        log(`Starting mission: "${prompt}"`, 'system');

        try {
            const response = await fetch('/api/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                
                // Save the last incomplete line back to the buffer
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const rawJson = line.substring(6).trim();
                        if (!rawJson) continue;
                        
                        try {
                            const data = JSON.parse(rawJson);
                            handleAgentStreamEvent(data);
                        } catch (e) {
                            console.error('Error parsing SSE event:', e);
                        }
                    }
                }
            }
        } catch (err) {
            log(`Error running agent: ${err.message}`, 'error');
        } finally {
            runBtn.disabled = false;
            runBtn.querySelector('.btn-text').innerText = 'Execute Mission';
            runBtn.querySelector('.loader').classList.add('hidden');
            await refreshData();
        }
    }

    // Process Stream Event
    function handleAgentStreamEvent(data) {
        if (data.status === 'completed') {
            log(data.message, 'system');
            return;
        }
        if (data.status === 'error') {
            log(data.message, 'error');
            return;
        }

        const node = data.node;
        const plan = data.plan || [];
        const currentStep = data.current_step;
        const logs = data.logs || [];

        // Log events
        logs.forEach(line => {
            let logType = 'system';
            if (line.includes('[Executor]')) logType = 'executor';
            else if (line.includes('[Planner]')) logType = 'planner';
            else if (line.includes('[Reporter]')) logType = 'reporter';
            
            log(line, logType);
        });

        // Update Plan UI
        if (plan.length > 0) {
            planSteps.innerHTML = '';
            plan.forEach((task, idx) => {
                const stepCard = document.createElement('div');
                
                let statusClass = 'pending';
                if (task.status === 'completed') {
                    statusClass = 'completed';
                } else if (idx === currentStep && data.node === 'executor') {
                    statusClass = 'running';
                }
                
                stepCard.className = `plan-step ${statusClass}`;
                stepCard.innerHTML = `
                    <span class="step-number">#${idx + 1}</span>
                    <span class="step-tool">${task.tool}</span>
                    <span class="step-desc">${task.description}</span>
                `;
                planSteps.appendChild(stepCard);
            });
        }
    }

    // Bind Event Listeners
    runBtn.addEventListener('click', runAgentMission);
    addMemoryBtn.addEventListener('click', addMemory);
    newMemoryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addMemory();
    });

    // Initial load
    loadConfig();
    refreshData();
});
