import pyttsx3

# Initialize TTS engine
engine = pyttsx3.init()

# Optional: set voice rate and volume
engine.setProperty('rate', 150)  # speed
engine.setProperty('volume', 1.0)  # max volume

# Ask user for text to speak
text = input("Enter text to speak: ")

# Speak the text
engine.say(text)
engine.runAndWait()

print("Done speaking!")
