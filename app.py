import subprocess
import re
from flask import Flask, request, jsonify, Response
from webvtt import WebVTT

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Predefined Sign Language Dictionary ---
signTokenDic = {
    'HELLO': 'gifs/hello.gif',
    'WORLD': 'gifs/world.gif',
    'HOW': 'gifs/how.gif',
    'YOU': 'gifs/you.gif',
    'DO': 'gifs/do.gif',
    'I': 'gifs/i.gif',
    'AM': 'gifs/am.gif',
    'FINE': 'gifs/fine.gif',
    'THANK': 'gifs/thank.gif',
    'GOOD': 'gifs/good.gif',
    'BAD': 'gifs/bad.gif',
    'YES': 'gifs/yes.gif',
    'NO': 'gifs/no.gif',
    'PLEASE': 'gifs/please.gif',
    'SORRY': 'gifs/sorry.gif',
    'WHAT': 'gifs/what.gif',
    'WHERE': 'gifs/where.gif',
    'WHEN': 'gifs/when.gif',
    'WHO': 'gifs/who.gif',
    'WHY': 'gifs/why.gif'
}

# --- API Endpoint for YouTube Transcription ---
@app.route('/transcribe-youtube', methods=['POST'])
def transcribe_youtube():
    """
    Accepts a YouTube URL, transcribes the audio, and returns sign language tokens
    for words in the signTokenDic.
    """
    # 1. Get the YouTube URL from the incoming JSON request
    data = request.get_json()
    if not data or 'youtube_url' not in data:
        return jsonify({"error": "youtube_url not found in request body"}), 400
    
    youtube_url = data['youtube_url']
    print(f"Received YouTube URL: {youtube_url}")

    ffmpeg_process = None
    whisper_process = None

    try:
        # 2. Use yt-dlp to get the best audio-only stream URL
        print("Fetching direct audio URL with yt-dlp...")
        yt_dlp_command = ["yt-dlp", "-f", "bestaudio", "-g", youtube_url]
        audio_url = subprocess.check_output(yt_dlp_command, text=True).strip()
        print(f"✅ Got audio stream URL.")

        # 3. Define the ffmpeg and whisper commands for the pipeline
        print("Starting ffmpeg and whisper pipeline...")
        ffmpeg_command = [
            "ffmpeg",
            "-i", audio_url,
            "-f", "wav",
            "-ar", "16000",
            "-ac", "1",
            "-",  # Pipe output to stdout
            "-loglevel", "error"
        ]
        
        whisper_command = [
            "whisper",
            "-",  # Read audio from stdin
            "--model", "base",
            "--output_format", "vtt"
        ]

        # 4. Start the ffmpeg process
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 5. Start the whisper process, piping ffmpeg's output to its input
        whisper_process = subprocess.Popen(
            whisper_command, 
            stdin=ffmpeg_process.stdout, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )

        # 6. Get the VTT output and any errors
        vtt_content_bytes, whisper_err_bytes = whisper_process.communicate()
        _, ffmpeg_err_bytes = ffmpeg_process.communicate()

        if ffmpeg_process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed with error: {ffmpeg_err_bytes.decode('utf-8')}")

        if whisper_process.returncode != 0:
            raise RuntimeError(f"Whisper failed with error: {whisper_err_bytes.decode('utf-8')}")

        print("✅ Pipeline finished successfully.")

        # 7. Parse VTT content and extract sign tokens
        vtt_content = vtt_content_bytes.decode('utf-8')
        sign_tokens = process_vtt_content(vtt_content)

        # 8. Return the sign tokens in the required format
        return jsonify({
            "success": True,
            "signTokens": sign_tokens
        })

    except subprocess.CalledProcessError as e:
        print(f"Error with yt-dlp: {e}")
        return jsonify({"error": "Failed to fetch audio from YouTube URL.", "details": str(e)}), 500
    except (RuntimeError, Exception) as e:
        print(f"An error occurred in the pipeline: {e}")
        return jsonify({"error": "An error occurred during transcription.", "details": str(e)}), 500

def process_vtt_content(vtt_content):
    """
    Parse VTT content and extract tokens that exist in signTokenDic.
    """
    sign_tokens = []
    try:
        # Parse VTT content
        vtt = WebVTT().from_string(vtt_content)
        for caption in vtt.captions:
            # Clean and tokenize the caption text
            text = caption.text.strip().upper()
            # Remove punctuation and split into words
            words = re.findall(r'\b\w+\b', text)
            # Filter words that exist in signTokenDic
            valid_tokens = [word for word in words if word in signTokenDic]
            
            if valid_tokens:
                sign_tokens.append({
                    "start": caption.start_in_seconds,
                    "end": caption.end_in_seconds,
                    "tokens": valid_tokens
                })
    except Exception as e:
        print(f"Error parsing VTT content: {e}")
        return []
    
    return sign_tokens

# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

# --- Run the App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)