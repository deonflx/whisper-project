from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Simple word-to-sign mapping
WORD_TO_SIGN_MAPPING = {
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
    'was': 'IS',
    'what': 'WHAT',
    'why': 'WHY',
    'with': 'WITH',
    'without': 'WITHOUT',
    'travel': 'TRAVEL',
    'video': 'VIDEO',
    'home': 'HOME',
    'drone': 'DRONE',
    'camera': 'CAMERA',
    'book': 'BOOK',
    'page': 'PAGE',
    'day': 'DAY',
    'fun': 'FUN',
    'idea': 'IDEA',
    'love': 'LOVE'
}

def time_to_seconds(time_str):
    try:
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
    lines = vtt_str.splitlines()
    sign_tokens = []
    invalid_timestamps = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == 'WEBVTT':
            i += 1
            continue
        if '-->' in line:
            try:
                time_part, *text_parts = line.split(maxsplit=2) if ']' not in line else line.split(']', 1)
                start_str, end_str = time_part.split(' --> ')
                start = time_to_seconds(start_str)
                end = time_to_seconds(end_str)
                if start is None or end is None:
                    invalid_timestamps.append(line)
                    i += 1
                    continue
                text = "".join(text_parts).strip()
                i += 1
                while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                    text += ' ' + lines[i].strip()
                    i += 1
                tokens = [
                    WORD_TO_SIGN_MAPPING[word.lower()]
                    for word in text.strip().replace('.', '').replace(',', '').split()
                    if word and word.lower() in WORD_TO_SIGN_MAPPING
                ]
                if tokens:
                    sign_tokens.append({"start": start, "end": end, "tokens": tokens})
            except ValueError:
                i += 1
                continue
        else:
            i += 1
    return sign_tokens, invalid_timestamps

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    if not data or 'subtitles' not in data:
        return jsonify({"success": False, "error": "subtitles not provided in request body"}), 400
    subtitles = data['subtitles']
    sign_tokens = []
    for sub in subtitles:
        text = sub.get('text', '').replace('.', '').replace(',', '').strip()
        tokens = [
            WORD_TO_SIGN_MAPPING[word.lower()]
            for word in text.split()
            if word.lower() in WORD_TO_SIGN_MAPPING
        ]
        if tokens:
            sign_tokens.append({
                "start": sub.get('start', 0),
                "end": sub.get('end', 0),
                "tokens": tokens
            })
    return jsonify({"success": True, "signTokens": sign_tokens})

@app.route('/transcribe-youtube', methods=['POST'])
def transcribe_youtube():
    data = request.get_json()
    if not data or 'youtube_url' not in data:
        return jsonify({"success": False, "error": "youtube_url not provided in request body"}), 400
    youtube_url = data['youtube_url']
    print(f"Received YouTube URL: {youtube_url}")
    try:
        yt_dlp_command = ["yt-dlp", "-f", "bestaudio", "-g", youtube_url]
        audio_url = subprocess.check_output(yt_dlp_command, text=True).strip()
        print(f"Got audio stream URL: {audio_url}")
        ffmpeg_command = [
            "ffmpeg", "-i", audio_url, "-f", "wav", "-ar", "16000", "-ac", "1", "-",
            "-loglevel", "error"
        ]
        whisper_command = ["whisper", "-", "--model", "base", "--output_format", "vtt"]
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        whisper_process = subprocess.Popen(
            whisper_command, stdin=ffmpeg_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        vtt_content_bytes, whisper_err_bytes = whisper_process.communicate()
        _, ffmpeg_err_bytes = ffmpeg_process.communicate()
        if ffmpeg_process.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {ffmpeg_err_bytes.decode('utf-8')}")
        if whisper_process.returncode != 0:
            raise RuntimeError(f"Whisper failed: {whisper_err_bytes.decode('utf-8')}")
        vtt_content = vtt_content_bytes.decode('utf-8')
        print(f"Raw VTT content:\n{vtt_content}")
        sign_tokens, invalid_timestamps = parse_vtt(vtt_content)
        response = {"success": True, "signTokens": sign_tokens}
        if invalid_timestamps:
            response["warnings"] = f"Skipped {len(invalid_timestamps)} invalid timestamps"
        return jsonify(response)
    except subprocess.CalledProcessError as e:
        print(f"Error with yt-dlp: {e}")
        return jsonify({"success": False, "error": "Failed to fetch audio from YouTube URL", "details": str(e)}), 500
    except (RuntimeError, Exception) as e:
        print(f"An error occurred in the pipeline: {e}")
        return jsonify({"success": False, "error": "An error occurred during transcription", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)