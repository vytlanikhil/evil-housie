const socket = io();

// Shared Update Logic
function updateDisplay(data) {
    const currentDisplay = document.getElementById('current-number-display');
    const remainingCount = document.getElementById('remaining-count');
    const historyList = document.getElementById('history-list');

    if (currentDisplay) {
        if (data.current_number !== null) {
            // Flash on change
            if (currentDisplay.textContent !== data.current_number.toString()) {
                currentDisplay.textContent = data.current_number;
                currentDisplay.classList.add('flash');
                setTimeout(() => currentDisplay.classList.remove('flash'), 200);
            }
        } else {
            currentDisplay.textContent = '--';
        }
    }

    if (remainingCount) {
        remainingCount.textContent = data.remaining_count;
    }

    if (historyList) {
        historyList.innerHTML = '';
        // Most recent at the top/front
        const recent = [...data.called_numbers].reverse();
        recent.forEach((num, index) => {
            const li = document.createElement('li');
            li.textContent = num;
            if (index === 0) {
                li.classList.add('newest');
            }
            historyList.appendChild(li);
        });
    }
}

// Mobile A (Caller/Display) Logic
function initMobileA() {
    console.log("Initialize App A");
    const grid = document.getElementById('grid');
    if (!grid) return;

    // Fast 1-90 board population
    const fragment = document.createDocumentFragment();
    for (let i = 1; i <= 90; i++) {
        const cell = document.createElement('div');
        cell.className = 'grid-cell';
        cell.id = `cell-${i}`;
        cell.textContent = i;
        fragment.appendChild(cell);
    }
    grid.appendChild(fragment);

    const nextBtn = document.getElementById('next-btn');
    nextBtn.addEventListener('click', () => {
        socket.emit('request_next_number');
    });

    socket.on('sync_state', (data) => {
        updateDisplay(data);
        updateGrid(data.called_numbers);
    });

    socket.on('next_number_generated', (data) => {
        updateDisplay(data);
        updateGrid(data.called_numbers);
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(new SpeechSynthesisUtterance("Number " + data.current_number));
        }
    });

    socket.on('error', (data) => {
        alert("Server Message: " + data.message);
    });

    socket.on('game_over', () => {
        const nextBtn = document.getElementById('next-btn');
        if (nextBtn) {
            nextBtn.disabled = true;
            nextBtn.textContent = 'Game Over';
        }
        alert("Game Over! The pool of numbers is complete.");
    });

    socket.on('game_reset', (data) => {
        updateDisplay(data);
        document.querySelectorAll('.grid-cell.called').forEach(cell => {
            cell.classList.remove('called');
        });
        const nextBtn = document.getElementById('next-btn');
        if (nextBtn) {
            nextBtn.disabled = false;
            nextBtn.textContent = 'Next Number';
        }
        if ('speechSynthesis' in window && window.location.pathname.includes('mobileA')) {
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(new SpeechSynthesisUtterance("Game Restarted"));
        }
    });

    const restartBtn = document.getElementById('restart-btn');
    if (restartBtn) {
        restartBtn.addEventListener('click', () => {
            if (confirm("Are you sure you want to restart the game?")) {
                socket.emit('restart_game');
            }
        });
    }

    function updateGrid(calledNumbers) {
        // Mark all called numbers incrementally
        calledNumbers.forEach(num => {
            const cell = document.getElementById(`cell-${num}`);
            if (cell && !cell.classList.contains('called')) {
                cell.classList.add('called');
            }
        });
    }
}

// Mobile B (Override) Logic
function initMobileB() {
    console.log("Initialize App B");
    const submitBtn = document.getElementById('override-submit');
    const inputField = document.getElementById('override-input');
    const statusMsg = document.getElementById('status-message');

    if (!submitBtn) return;

    let statusTimeout;
    function showStatus(msg, isError = false) {
        statusMsg.textContent = msg;
        statusMsg.className = 'status-box ' + (isError ? 'error' : 'success');
        clearTimeout(statusTimeout);
        statusTimeout = setTimeout(() => { 
            statusMsg.textContent = ''; 
            statusMsg.className = 'status-box';
        }, 4000);
    }

    submitBtn.addEventListener('click', () => {
        const val = inputField.value;
        if (!val) {
            showStatus("Provide a valid integer.", true);
            return;
        }
        socket.emit('override_number', { number: val });
        inputField.value = '';
        inputField.focus(); // Keep focus for quick entries
    });
    
    // Quick enter injection
    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            submitBtn.click();
        }
    });

    socket.on('sync_state', (data) => {
        updateDisplay(data);
    });

    socket.on('next_number_generated', (data) => {
        updateDisplay(data);
    });

    socket.on('override_success', (data) => {
        showStatus(data.message);
    });

    socket.on('error', (data) => {
        showStatus(data.message, true);
    });
}

socket.on('connect', () => {
    console.log("WebSocket Established.");
});

socket.on('disconnect', () => {
    console.log("Connection lost. Socket.io will automatically reconnect.");
});
