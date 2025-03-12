import speech_recognition as sr

def listen_phrase(recognizer, microphone, pause_threshold):
    """
    Listens for a phrase using the given pause_threshold.
    The pause_threshold determines how many seconds of silence signal
    the end of a phrase.
    """
    recognizer.pause_threshold = pause_threshold
    with microphone as source:
        print("Listening...")
        audio = recognizer.listen(source)
    return audio

def main():
    # Initialize recognizer and microphone.
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    # Calibrate the microphone to ambient noise.
    print("Calibrating microphone for ambient noise... Please wait.")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    print("Calibration complete.\n")

    while True:
        try:
            # Listen with a lower pause threshold for faster phrase detection.
            print("Waiting for activation keyword...")
            audio = listen_phrase(recognizer, mic, pause_threshold=0.8)
            
            try:
                phrase = recognizer.recognize_google(audio)
                print(f"Heard (keyword phase): '{phrase}'")
            except sr.UnknownValueError:
                print("Could not understand audio.")
                continue

            # Check if the activation keyword is in the phrase.
            if "activate" in phrase.lower():
                print("Activation keyword detected!")
                print("Listening for command (will end after 2 seconds of silence)...")
                
                # Listen for the command with a longer pause_threshold (2 seconds).
                audio_command = listen_phrase(recognizer, mic, pause_threshold=2.0)
                try:
                    command = recognizer.recognize_google(audio_command)
                    print(f"Command captured: '{command}'\n")
                    # Here you can add further processing for the captured command.
                except sr.UnknownValueError:
                    print("Could not understand command audio.\n")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
