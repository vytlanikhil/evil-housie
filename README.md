# EVIL-HOUSIE (Tambola) System 🎱

A production-ready, real-time multi-device Housie (Tambola) system. Designed to be run over a Local Area Network, this project features a central authoritative Python backend and two distinct web clients. It includes a stealth-override capability allowing an administrator to invisibly control the sequence of drawn numbers!

## Features 🚀
- **Real-time Synchronization:** Built on Flask-SocketIO for instant WebSocket communication between clients.
- **Stealth Override System:** Dedicated Controller UI (Mobile B) allows an admin to inject specific numbers up to 90. Injections are randomized with a 2-5 second delay to appear perfectly natural and stochastic.
- **Fail-safe State Persistence:** The entire game state auto-saves to `state.json`. If the server crashes or loses power, rebooting seamlessly picks up where the game left off exactly.
- **Race Condition Prevention:** Fully synchronized number generation utilizing strict thread locking (`threading.Lock()`).
- **Text-to-Speech (TTS):** Integrated HTML5 Web Speech API directly in the Mobile A front-end to announce drawn numbers synchronously.
- **Rate-Limited Controls:** Strict rate limiting is implemented to prevent system flooding from the Override controller.

## Setup Instructions 🛠️

### Prerequisites
- Python 3.8+
- Active Local Area Network (Wi-Fi or Ethernet)

### Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/vytlanikhil/evil-housie.git
   cd evil-housie
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Server
Start the central backend server:
```bash
python server.py
```
The application binds to `0.0.0.0:5000`, making it accessible across your entire LAN.

### Accessing the Clients
Find the Internal IP address of the PC running the server (e.g., `192.168.1.50`).

1. **Mobile A (Caller & Display):** Open `http://<YOUR_PC_IP>:5000/mobileA` on a tablet or phone to display the Housie Caller, the 1-90 board, and the drawn number history.
2. **Mobile B (Stealth Controller):** Open `http://<YOUR_PC_IP>:5000/mobileB` on the admin's hidden device to inject priority numbers securely overriding the RNG.

## Engineering Highlights 🧠
- **Idempotency & Concurrency:** All operations mapping to `remaining_numbers` and `override_queue` are computationally safe and bound by memory locks.
- **Graceful Exhaustion:** The system gracefully handles an empty pool (all 90 numbers called) by seamlessly locking UI components, restricting API calls, and awaiting a manual "Restart Game" signal.
