import os
import json
import random
import time
import logging
import threading
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
# Allow cross domain / local IPs
app.config['SECRET_KEY'] = 'secret-housie-key'
socketio = SocketIO(app, cors_allowed_origins='*')

STATE_FILE = 'state.json'
LOG_FILE = 'logs.txt'

# Lock for thread-safe state mutations
state_lock = threading.Lock()

# Central state
state = {
    "remaining_numbers": list(range(1, 91)),
    "called_numbers": [],
    "last_called_number": None,
    "game_active": True
}
override_queue = []

# Rate limiting map { session_id/ip : last_timestamp }
rate_limits = {}

# Logging Setup
logger = logging.getLogger("housie")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console logger for debugging
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def load_state():
    """ Safe loading of previous game state. """
    global state
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                loaded = json.load(f)
                state["remaining_numbers"] = loaded.get("remaining_numbers", list(range(1, 91)))
                state["called_numbers"] = loaded.get("called_numbers", [])
                state["last_called_number"] = loaded.get("last_called_number", None)
                state["game_active"] = loaded.get("game_active", True)
            logger.info("Previous session state loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

def save_state():
    """ Safe state persistence """
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({
                "remaining_numbers": state["remaining_numbers"],
                "called_numbers": state["called_numbers"],
                "last_called_number": state["last_called_number"],
                "game_active": state["game_active"]
            }, f)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")

# Call load_state on startup
load_state()

def get_next_number():
    """ Atomic number generation algorithm """
    with state_lock:
        if not state["game_active"]:
            return None, "Game over."

        if not state["remaining_numbers"]:
            state["game_active"] = False
            save_state()
            return None, "Empty pool."

        number = None
        
        # 1. Inspect Override Queue
        while override_queue:
            ov = override_queue.pop(0)
            if ov in state["remaining_numbers"]:
                number = ov
                logger.info(f"Override validated and used: {number}")
                break
            else:
                logger.warning(f"Override rejected: {ov} is not in remaining_numbers (already called or invalid).")
        
        # 2. Random selection if no valid override
        if number is None:
            if not state["remaining_numbers"]:
                state["game_active"] = False
                save_state()
                return None, "Empty pool."
            number = random.choice(state["remaining_numbers"])
            logger.info(f"Random number drawn: {number}")

        # 3. Update state collections
        state["remaining_numbers"].remove(number)
        state["called_numbers"].append(number)
        state["last_called_number"] = number
        
        # 4. Save state block
        save_state()
        
        return number, None

def get_sync_data():
    """ Data wrapper for clients """
    with state_lock:
        return {
            "current_number": state["last_called_number"],
            "called_numbers": state["called_numbers"],
            "remaining_count": len(state["remaining_numbers"])
        }

# UI Routes
@app.route('/')
def redirect_to_a():
    return render_template('mobileA.html')

@app.route('/mobileA')
def mobile_a():
    return render_template('mobileA.html')

@app.route('/mobileB')
def mobile_b():
    return render_template('mobileB.html')

# Socket Routes
@socketio.on('connect')
def handle_connect():
    emit('sync_state', get_sync_data())

@socketio.on('request_sync')
def handle_request_sync():
    emit('sync_state', get_sync_data())

@socketio.on('request_next_number')
def handle_request_next_number(data=None):
    number, error = get_next_number()
    if error:
        if error == "Empty pool.":
            socketio.emit('game_over')
        else:
            emit('error', {"message": error})
    else:
        socketio.emit('next_number_generated', get_sync_data())

def reset_game():
    with state_lock:
        state["remaining_numbers"] = list(range(1, 91))
        state["called_numbers"] = []
        state["last_called_number"] = None
        state["game_active"] = True
        override_queue.clear()
        save_state()
    socketio.emit('game_reset', get_sync_data())

@socketio.on('restart_game')
def handle_restart_game():
    reset_game()

def delayed_override(number):
    """ Stealth operation: Add random delay before queueing """
    delay = random.uniform(2.0, 5.0)
    time.sleep(delay)
    with state_lock:
        override_queue.append(number)
    logger.info(f"Stealth override injected after {delay:.2f}s delay: {number}")

@socketio.on('override_number')
def handle_override(data):
    # Differentiate clients
    sid = request.sid
    now = time.time()
    
    # Check rate limits to prevent rapid-fire overriding
    if sid in rate_limits:
        if now - rate_limits[sid] < 2.0:
            emit('error', {"message": "Rate limited. One override per 2 seconds max."})
            return
            
    rate_limits[sid] = now

    if not data or "number" not in data:
        emit('error', {"message": "Payload missing 'number' parameter."})
        return

    # Basic input checks
    try:
        val = int(data["number"])
    except ValueError:
        emit('error', {"message": "Input validation failed: Must be an integer."})
        logger.error(f"Integrity warning: User submitted non-integer override {data['number']}")
        return

    if val < 1 or val > 90:
        emit('error', {"message": "Input validation failed: Allowed range is 1-90."})
        return

    # Check for duplicate override logic
    with state_lock:
        if val in state["called_numbers"]:
            emit('error', {"message": f"Wait, {val} was already called."})
            logger.warning(f"Duplicate override blocked: User targeted {val} but already drawn.")
            return

    # Deploy thread so as not to block incoming requests
    threading.Thread(target=delayed_override, args=(val,), daemon=True).start()
    emit('override_success', {"message": f"Strategic override code {val} transmitted."})
    logger.info(f"Client {sid} initiated stealth override protocol for {val}.")

if __name__ == '__main__':
    # Launch on 0.0.0.0 to enable LAN play over WiFi 
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
