import subprocess
from flask import Flask, request, jsonify, Response

# --- Flask App Initialization ---
app = Flask(__name__)

# --- API Endpoint for YouTube Transcription ---
@app.route('/transcribe-youtube', methods=['POST'])
def transcribe_youtube():
    """
    Accepts a YouTube URL in a JSON POST request, transcribes the audio,
    and returns the transcription as a VTT file.
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
            "-loglevel", "error" # Suppress verbose ffmpeg info
        ]
        
        whisper_command = [
            "whisper",
            "-", # Read audio from stdin
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
            # NOTE: Removed `text=True` as ffmpeg outputs raw bytes, not text.
        )

        # MISTAKE REMOVED: Do NOT close ffmpeg_process.stdout here.
        # Closing it manually in the parent process causes a deadlock because
        # the parent holds the pipe open, preventing `whisper` from ever
        # detecting the end of the stream.
        # ffmpeg_process.stdout.close() # <-- THIS LINE WAS REMOVED

        # 6. Get the final VTT output and any errors.
        # communicate() reads all data and waits for the process to finish.
        vtt_content_bytes, whisper_err_bytes = whisper_process.communicate()
        
        # Also check ffmpeg for errors
        _, ffmpeg_err_bytes = ffmpeg_process.communicate()

        if ffmpeg_process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed with error: {ffmpeg_err_bytes.decode('utf-8')}")

        # Check if Whisper finished successfully
        if whisper_process.returncode != 0:
            raise RuntimeError(f"Whisper failed with error: {whisper_err_bytes.decode('utf-8')}")

        print("✅ Pipeline finished successfully.")
        
        # 7. Return the VTT content as a downloadable file
        # The output from the process is bytes, which is exactly what Response needs.
        return Response(
            vtt_content_bytes,
            mimetype="text/vtt",
            headers={"Content-Disposition": "attachment; filename=transcription.vtt"}
        )

    except subprocess.CalledProcessError as e:
        # This catches errors if the yt-dlp command fails
        print(f"Error with yt-dlp: {e}")
        return jsonify({"error": "Failed to fetch audio from YouTube URL.", "details": str(e)}), 500
    except (RuntimeError, Exception) as e:
        # This catches our custom errors and any other unexpected ones
        print(f"An error occurred in the pipeline: {e}")
        return jsonify({"error": "An error occurred during transcription.", "details": str(e)}), 500

# --- Run the App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)