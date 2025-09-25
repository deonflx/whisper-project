import subprocess
from flask import Flask, request, jsonify

# --- Flask App Initialization ---
app = Flask(__name__)

# Simple word-to-sign mapping

WORD_TO_SIGN_MAPPING = {
    # Original Words
    'hello': 'HELLO',
    'hi': 'HELLO', 
    'world': 'WORLD',
    'how': 'HOW',
    'are': 'YOU',
    'you': 'YOU',
    'doing': 'DO',
    'do': 'DO',
    'i': 'I',
    'am': 'AM',
    'fine': 'FINE',
    'good': 'GOOD',
    'thank': 'THANK',
    'thanks': 'THANK',
    'yes': 'YES',
    'no': 'NO',
    'please': 'PLEASE',
    'sorry': 'SORRY',
    'bad': 'BAD',
    'nice': 'GOOD',
    'great': 'GOOD',
    'awesome': 'GOOD',

    # --- New Words from Transcription ---
    'again': 'AGAIN',
    'air': 'AIR',
    'all': 'ALL',
    'animal': 'ANIMAL',
    'at': 'AT',
    'because': 'BECAUSE',
    'bottom': 'BOTTOM',
    'die': 'DIE',
    'died': 'DIE',
    'down': 'DOWN',
    'fire': 'FIRE',
    'for': 'FOR',
    'from': 'FROM',
    'gas': 'GAS',
    'get': 'GET',
    'got': 'GET',
    'happen': 'HAPPEN',
    'happened': 'HAPPEN',
    'human': 'HUMAN',
    'in': 'IN',
    'is': 'IS',
    'it': 'IT',
    'kill': 'KILL',
    'killed': 'KILL',
    'lake': 'LAKE',
    'live': 'LIVE',
    'lived': 'LIVE',
    'make': 'MAKE',
    'minute': 'MINUTE',
    'near': 'NEAR',
    'never': 'NEVER',
    'night': 'NIGHT',
    'old': 'OLD',
    'on': 'ON',
    'one': 'ONE',
    'people': 'PEOPLE',
    'sat': 'SIT',
    'see': 'SEE',
    'sit': 'SIT',
    'sleep': 'SLEEP',
    'story': 'STORY',
    'sure': 'SURE',
    'that': 'THAT',
    'their': 'THEIR',
    'them': 'THEM',
    'they': 'THEY',
    'this': 'THIS',
    'today': 'TODAY',
    'tomorrow': 'TOMORROW',
    'top': 'TOP',
    'under': 'UNDER',
    'village': 'VILLAGE',
    'volcano': 'VOLCANO',
    'was': 'IS', # Mapping past tense to the base sign
    'what': 'WHAT',
    'why': 'WHY',
    'with': 'WITH',
    'without': 'WITHOUT'
}

def time_to_seconds(time_str):
    """
    Convert VTT timestamp (e.g., [hh:mm:ss.mmm] or hh:mm:ss.mmm) to seconds as float.
    Returns None if the timestamp is invalid.
    """
    try:
        # FIX: More robustly remove whitespace and any surrounding brackets
        time_str = time_str.strip().strip('[]')
        parts = time_str.split(':')
        ms = 0.0
        if len(parts) == 3:
            h, m, s = parts
            if '.' in s:
                s, ms_str = s.split('.')
                ms = float(ms_str) / 1000
            return float(h) * 3600 + float(m) * 60 + float(s) + ms
        elif len(parts) == 2:
            m, s = parts
            if '.' in s:
                s, ms_str = s.split('.')
                ms = float(ms_str) / 1000
            return float(m) * 60 + float(s) + ms
        else:
            print(f"Invalid timestamp format: {time_str}")
            return None
    except (ValueError, Exception) as e:
        print(f"Error parsing timestamp '{time_str}': {e}")
        return None

def parse_vtt(vtt_str):
    """
    Parse VTT content into list of dicts with start, end, and tokens (filtered by WORD_TO_SIGN_MAPPING).
    Skips invalid timestamps and logs them for debugging.
    """
    lines = vtt_str.splitlines()
    sign_tokens = []
    invalid_timestamps = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == 'WEBVTT':
            i += 1
            continue
        
        # FIX: Handle cases where timestamp and text are on the same line
        if '-->' in line:
            try:
                # Separate the timestamp part from the potential text on the same line
                time_part, *text_on_same_line_parts = line.split(maxsplit=2) if ']' not in line else line.split(']', 1)
                start_str, end_str = time_part.split(' --> ')
                
                start = time_to_seconds(start_str)
                end = time_to_seconds(end_str)

                if start is None or end is None:
                    invalid_timestamps.append(line)
                    i += 1
                    continue
                
                # Join any text found on the same line
                text = "".join(text_on_same_line_parts).strip()
                i += 1
                
                # Collect any additional multi-line text
                while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                    text += ' ' + lines[i].strip()
                    i += 1

                # Filter words that are in WORD_TO_SIGN_MAPPING (case-insensitive)
                tokens = [
                    WORD_TO_SIGN_MAPPING[word.lower()] 
                    for word in text.strip().replace('.', '').replace(',', '').split() 
                    if word and word.lower() in WORD_TO_SIGN_MAPPING
                ]
                
                if tokens:
                    sign_tokens.append({
                        "start": start,
                        "end": end,
                        "tokens": tokens
                    })

            except ValueError:
                # This handles malformed '-->' lines that can't be split properly
                i += 1
                continue
        else:
            i += 1
            
    return sign_tokens, invalid_timestamps


# --- API Endpoint for YouTube Transcription ---
@app.route('/transcribe-youtube', methods=['POST'])
def transcribe_youtube():
    """
    Accepts a YouTube URL in a JSON POST request, transcribes the audio,
    parses the VTT transcription, and returns relevant words from WORD_TO_SIGN_MAPPING with timestamps as JSON.
    """
    # 1. Get the YouTube URL from the incoming JSON request
    data = request.get_json()
    if not data or 'youtube_url' not in data:
        return jsonify({"success": False, "error": "youtube_url not provided in request body"}), 400
    
    youtube_url = data['youtube_url']
    print(f"Received YouTube URL: {youtube_url}")

    ffmpeg_process = None
    whisper_process = None

    try:
        # 2. Use yt-dlp to get the best audio-only stream URL
        print("Fetching direct audio URL with yt-dlp...")
        yt_dlp_command = ["yt-dlp", "-f", "bestaudio", "-g", youtube_url]
        audio_url = subprocess.check_output(yt_dlp_command, text=True).strip()
        print(f"✅ Got audio stream URL: {audio_url}")

        # 3. Define the ffmpeg and whisper commands for the pipeline
        print("Starting ffmpeg and whisper pipeline...")
        ffmpeg_command = [
            "ffmpeg",
            "-i", audio_url,
            "-f", "wav",
            "-ar", "16000",
            "-ac", "1",
            "-",  # Pipe output to stdout
            "-loglevel", "error"  # Suppress verbose ffmpeg info
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

        # 6. Get the final VTT output and any errors
        vtt_content_bytes, whisper_err_bytes = whisper_process.communicate()
        _, ffmpeg_err_bytes = ffmpeg_process.communicate()

        if ffmpeg_process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed with error: {ffmpeg_err_bytes.decode('utf-8')}")

        if whisper_process.returncode != 0:
            raise RuntimeError(f"Whisper failed with error: {whisper_err_bytes.decode('utf-8')}")

        print("✅ Pipeline finished successfully.")
        
        # 7. Parse the VTT content into the desired JSON format
        vtt_content = vtt_content_bytes.decode('utf-8')
        print(f"Raw VTT content:\n{vtt_content}")  # Log for debugging
        sign_tokens, invalid_timestamps = parse_vtt(vtt_content)
        
        response = {
            "success": True,
            "signTokens": sign_tokens
        }
        if invalid_timestamps:
            response["warnings"] = f"Skipped {len(invalid_timestamps)} invalid timestamps: {invalid_timestamps}"
        
        return jsonify(response)

    except subprocess.CalledProcessError as e:
        print(f"Error with yt-dlp: {e}")
        return jsonify({"success": False, "error": "Failed to fetch audio from YouTube URL.", "details": str(e)}), 500
    except (RuntimeError, Exception) as e:
        print(f"An error occurred in the pipeline: {e}")
        return jsonify({"success": False, "error": "An error occurred during transcription.", "details": str(e)}), 500

# --- Run the App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)