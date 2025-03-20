def play_beep(frequency, duration):
    if platform.system() == "Darwin":  # macOS
        subprocess.call(["afplay", "/System/Library/Sounds/Ping.aiff"])
    elif platform.system() == "Linux":
        subprocess.call(["paplay", "/usr/share/sounds/freedesktop/stereo/bell.oga"])
    elif platform.system() == "Windows":
        import winsound
        winsound.Beep(frequency, duration)  # 1000 Hz for 500 milliseconds