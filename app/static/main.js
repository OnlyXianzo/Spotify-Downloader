document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    const modeText = document.getElementById('modeText');
    const form = document.getElementById('downloadForm');
    const urlInput = document.getElementById('urlInput');
    const taskList = document.getElementById('taskList');

    // Theme Handling
    themeToggle.addEventListener('click', () => {
        html.classList.toggle('dark');
        modeText.textContent = html.classList.contains('dark') ? 'Dark' : 'Light';
    });

    // Form Submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;

        try {
            const formData = new FormData();
            formData.append('url', url);
            await fetch('/download', {
                method: 'POST',
                body: formData
            });
            urlInput.value = '';
        } catch (err) {
            console.error('Failed to add download:', err);
            alert('Failed to add download');
        }
    });

    // WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws`);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        renderTasks(data);
        updateStats(data);
    };

    function updateStats(tasks) {
        document.getElementById('countQueued').textContent = tasks.filter(t => t.status === 'queued').length;
        document.getElementById('countDownloading').textContent = tasks.filter(t => t.status === 'downloading' || t.status === 'processing_metadata').length;
        document.getElementById('countFinished').textContent = tasks.filter(t => t.status === 'finished').length;
    }

    function renderTasks(tasks) {
        if (tasks.length === 0) {
            taskList.innerHTML = '<div class="text-center text-gray-500 py-8">No active downloads</div>';
            return;
        }

        taskList.innerHTML = tasks.map(task => `
            <div class="flex items-center gap-4 p-4 rounded-lg bg-gray-50 dark:bg-[#282828] transition-all">
                <div class="w-12 h-12 bg-gray-300 rounded overflow-hidden flex-shrink-0">
                    ${task.cover ? `<img src="${task.cover}" class="w-full h-full object-cover">` : ''}
                </div>
                <div class="flex-1 min-w-0">
                    <h3 class="font-medium truncate text-gray-900 dark:text-white">${task.name !== 'Unknown' ? task.name : task.query}</h3>
                    <p class="text-sm text-gray-500 dark:text-gray-400 truncate">${task.artist}</p>

                    ${task.status === 'downloading' ? `
                        <div class="w-full bg-gray-200 rounded-full h-1.5 mt-2 dark:bg-gray-700 overflow-hidden">
                            <div class="bg-blue-600 h-1.5 rounded-full animate-pulse" style="width: 100%"></div>
                        </div>
                    ` : ''}
                     ${task.status === 'finished' ? `
                        <div class="w-full bg-gray-200 rounded-full h-1.5 mt-2 dark:bg-gray-700 overflow-hidden">
                            <div class="bg-spotgreen h-1.5 rounded-full" style="width: 100%"></div>
                        </div>
                    ` : ''}
                </div>
                <div class="flex-shrink-0">
                    ${getStatusBadge(task)}
                </div>
            </div>
        `).join('');
    }

    function getStatusBadge(task) {
        const classes = {
            'queued': 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
            'processing_metadata': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
            'downloading': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
            'finished': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
            'failed': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
        };

        let label = task.status;
        if (task.status === 'processing_metadata') label = 'Searching...';
        if (task.status === 'downloading') label = 'Downloading...';

        return `<span class="px-3 py-1 rounded-full text-xs font-medium ${classes[task.status] || classes['queued']}">
            ${label.toUpperCase()}
        </span>`;
    }
});
