import pyttsx3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TTS_Local")

# Init engine
engine = pyttsx3.init()

# Tweaks for speed and volume
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

text = input("Enter text to speak: ")

engine.say(text)
engine.runAndWait()

logger.info("Done speaking!")