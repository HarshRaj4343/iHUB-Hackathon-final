from flask import Flask, render_template, jsonify, request
from emotion_detector import get_classroom_emotion
from audio_detector import check_classroom_audio
from Speech_analyzer import SpeechAnalyzer
import threading
import time
import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

app = Flask(__name__)

# Initialize speech analyzer
speech_analyzer = SpeechAnalyzer()

# Global data
dashboard_data = {
    'engagement_score': 50,
    'emotion': 'neutral',
    'audio_state': 'quiet',
    'teacher_pace': 'unknown',
    'teacher_wpm': 0,
    'teacher_tone': 'unknown',
    'nudge': 'Click "Analyze My Teaching" to get started!',
    'speech_nudge': '',
    'timestamp': time.time(),
    'status': 'Ready',
    'analyzing_speech': False  # New flag
}

# Lock for thread-safe updates
data_lock = threading.Lock()

def update_student_data():
    """Background thread that only updates STUDENT metrics (emotion + audio)"""
    global dashboard_data
    
    time.sleep(5)
    cycle = 0
    
    while True:
        try:
            # Only analyze if NOT currently analyzing speech
            with data_lock:
                if dashboard_data['analyzing_speech']:
                    time.sleep(5)
                    continue
            
            cycle += 1
            print(f"\n{'='*60}")
            print(f"🔄 Student analysis cycle {cycle}")
            print(f"{'='*60}")
            
            # Update status
            with data_lock:
                dashboard_data['status'] = 'Analyzing students...'
            
            # 1. Get student emotion (~5 seconds)
            print("📸 Analyzing student emotions...")
            emotion = get_classroom_emotion()
            print(f"✅ Emotion: {emotion}")
            
            # 2. Get classroom audio (~3 seconds)
            print("🎧 Analyzing classroom audio...")
            audio_state, audio_message = check_classroom_audio(duration=3)
            print(f"✅ Audio: {audio_state}")
            
            # 3. Calculate engagement score
            score = 50  # base
            
            # Student emotion impact
            if emotion in ['happy', 'neutral', 'surprise']:
                score += 20
            elif emotion in ['sad', 'angry', 'fear']:
                score -= 20
            
            # Audio impact
            if audio_state == 'silent':
                score -= 20
            elif audio_state == 'active':
                score += 10
            
            # Get current teacher metrics (don't recalculate)
            with data_lock:
                teacher_pace = dashboard_data.get('teacher_pace', 'unknown')
                teacher_wpm = dashboard_data.get('teacher_wpm', 0)
                teacher_tone = dashboard_data.get('teacher_tone', 'unknown')
                speech_nudge = dashboard_data.get('speech_nudge', '')
            
            # Teacher pace impact (only if analyzed)
            if teacher_pace == 'too_fast':
                score -= 15
            elif teacher_pace == 'too_slow':
                score -= 10
            elif teacher_pace == 'good':
                score += 5
            
            # Teacher tone impact (only if analyzed)
            if teacher_tone == 'monotone':
                score -= 15
            elif teacher_tone == 'engaging':
                score += 10
            
            score = max(0, min(100, score))
            
            # 4. Generate main nudge
            nudge = "✅ All good! Keep going."
            if score < 40:
                nudge = "⚠️ Low engagement! Try asking a question or showing an example."
            elif score < 60:
                nudge = "⚡ Engagement dropping. Consider a quick activity or recap."
            
            # 5. Update dashboard (thread-safe)
            with data_lock:
                dashboard_data['engagement_score'] = score
                dashboard_data['emotion'] = emotion
                dashboard_data['audio_state'] = audio_state
                dashboard_data['nudge'] = nudge
                dashboard_data['timestamp'] = time.time()
                dashboard_data['status'] = 'Active'
            
            print(f"\n📊 Updated: Score={score}, Emotion={emotion}, Audio={audio_state}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"❌ Error in student analysis: {e}")
            import traceback
            traceback.print_exc()
            with data_lock:
                dashboard_data['status'] = f'Error: {str(e)}'
        
        # Wait before next cycle
        time.sleep(10)


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/data')
def get_data():
    """Return current dashboard data"""
    with data_lock:
        return jsonify(dashboard_data)


@app.route('/analyze-speech', methods=['POST'])
def analyze_speech():
    """Triggered when teacher clicks the button"""
    
    global dashboard_data
    
    # Check if already analyzing
    with data_lock:
        if dashboard_data['analyzing_speech']:
            return jsonify({
                'status': 'error',
                'message': 'Already analyzing speech. Please wait.'
            })
        
        # Set flag to prevent student analysis during speech recording
        dashboard_data['analyzing_speech'] = True
        dashboard_data['status'] = 'Get ready to speak...'
        dashboard_data['speech_nudge'] = 'Preparing to record...'
    
    # Run speech analysis in background thread
    def analyze():
        global dashboard_data
        
        try:
            print("\n" + "="*60)
            print("🎤 TEACHER SPEECH ANALYSIS STARTED")
            print("="*60)
            
            # Update status
            with data_lock:
                dashboard_data['status'] = 'Recording your speech...'
                dashboard_data['speech_nudge'] = '🔴 Recording for 10 seconds... Speak naturally!'
            
            # Wait 2 seconds for teacher to get ready
            time.sleep(2)
            
            # Analyze speech (takes ~10 seconds)
            result = speech_analyzer.analyze_teacher_speech(duration=10)
            
            print(f"✅ Analysis complete!")
            print(f"   Pace: {result['pace']} ({result['wpm']} WPM)")
            print(f"   Tone: {result['tone']}")
            print(f"   Nudge: {result['nudge']}")
            
            # Update dashboard with results
            with data_lock:
                dashboard_data['teacher_pace'] = result['pace']
                dashboard_data['teacher_wpm'] = result['wpm']
                dashboard_data['teacher_tone'] = result['tone']
                dashboard_data['speech_nudge'] = result['nudge']
                dashboard_data['status'] = 'Analysis complete!'
                dashboard_data['analyzing_speech'] = False
            
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"❌ Speech analysis error: {e}")
            import traceback
            traceback.print_exc()
            
            with data_lock:
                dashboard_data['speech_nudge'] = f'Error analyzing speech: {str(e)}'
                dashboard_data['status'] = 'Error occurred'
                dashboard_data['analyzing_speech'] = False
    
    # Start analysis in background
    thread = threading.Thread(target=analyze, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'success',
        'message': 'Speech analysis started. Recording will begin in 2 seconds...'
    })


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting Shiksha-Pulse Dashboard")
    print("=" * 60)
    print("📊 Dashboard: http://localhost:5000")
    print("⚠️  Grant camera/mic permissions if prompted")
    print("🎤 Click 'Analyze My Teaching' button to analyze your speech")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Start background thread for student analysis only
    thread = threading.Thread(target=update_student_data, daemon=True)
    thread.start()
    
    # Run Flask
    app.run(debug=False, port=5000, threaded=True)
