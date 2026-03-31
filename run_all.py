import subprocess
import time
import sys
import os

# --- CONFIGURATION ---
SCRIPTS = {
    "DASHBOARD (The UI)": [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port=8501"],
    "HUNTER (Insta Watcher)": [sys.executable, "python_scripts/instagram_watcher.py"],
    "BRAIN (Orchestrator)": [sys.executable, "python_scripts/master_orchestrator.py"],
    "CLOSER (WA Poster)": [sys.executable, "python_scripts/whatsapp_poster.py"]
}

processes = {}

def start_script(name, command):
    """Starts a script and returns the process object."""
    print(f"🚀 Starting {name}...")
    # Using 'startupinfo' on Windows to hide console windows if needed, 
    # but here we keep them in one terminal as requested.
    return subprocess.Popen(command)

def monitor():
    """Main monitor loop with heartbeat and auto-restart."""
    print("\n" + "="*50)
    print("🌟 DIGITAL FTE: ALL-IN-ONE ORCHESTRATOR 🌟")
    print("="*50 + "\n")

    # Initial Start
    for name, cmd in SCRIPTS.items():
        processes[name] = start_script(name, cmd)

    try:
        while True:
            time.sleep(30)
            print(f"\n💓 HEARTBEAT MONITOR [{time.strftime('%H:%M:%S')}]")
            print("-" * 40)
            
            for name, cmd in SCRIPTS.items():
                proc = processes[name]
                
                # poll() returns None if process is still running
                if proc.poll() is None:
                    print(f"✅ {name:25} | STATUS: ALIVE")
                else:
                    exit_code = proc.poll()
                    print(f"🛑 {name:25} | STATUS: CRASHED (Code: {exit_code})")
                    print(f"🔄 Auto-Restarting {name}...")
                    processes[name] = start_script(name, cmd)
            
            print("-" * 40)

    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down all systems...")
        for name, proc in processes.items():
            print(f"👋 Terminating {name}...")
            proc.terminate()
        print("✅ All systems offline. Goodbye!")

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    monitor()
