import sounddevice as sd
import numpy as np

def check_classroom_audio(duration=5):
   
    
    print("🎤 Listening for", duration, "seconds...")
    

    sample_rate = 44100
    recording = sd.rec(int(duration * sample_rate), 
                      samplerate=sample_rate, 
                      channels=1)
    sd.wait()
    

    volume = np.abs(recording).mean()
    
    print(f"Volume level: {volume}")
    
 
    if volume < 0.002:  # Extremely sensitive to silence
        return "silent", "⚠️ Dead silence - students may be confused"
    elif volume < 0.01:  # Extremely sensitive to quiet noise
        return "quiet", "✅ Normal classroom sound"
    else:  # Considers even very low volumes as active
        return "active", "💬 Active discussion happening"

if __name__ == "__main__":
    state, message = check_classroom_audio()
    print(message)
