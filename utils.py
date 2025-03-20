import platform
import subprocess

def play_beep(frequency, duration):
    system = platform.system()
    if system == "Darwin":  # macOS
        subprocess.call(["afplay", "/System/Library/Sounds/Ping.aiff"])
    elif system == "Linux":
        subprocess.call(["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"])
    elif system == "Windows":
        import winsound
        winsound.Beep(frequency, duration)  # 1000 Hz for 500 milliseconds