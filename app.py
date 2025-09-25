import os
import uuid
import subprocess
from flask import Flask, request, jsonify, Response
from werkzeug.utils import secure_filename

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Helper Function ---
def allowed_file(filename: str) -> bool:
    """Checks if the filename has an allowed extension."""
    ALLOWED_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg', 'mp4', 'mov', 'webm'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- API Endpoint ---
@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if not file or not file.filename:
        return jsonify({"error": "No selected file"}), 400

    if allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        _root, file_extension = os.path.splitext(original_filename)
        
        unique_filename = str(uuid.uuid4())
        audio_filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename + file_extension)
        # Define the path for the VTT file that Whisper will create
        vtt_filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename + ".vtt")
        
        try:
            # 1. Save the uploaded audio file
            file.save(audio_filepath)
            print(f"Audio saved to {audio_filepath}")

            # 2. Build and run the Whisper command-line tool as a subprocess
            command = [
                "whisper",
                audio_filepath,
                "--model", "base",
                "--output_format", "vtt",
                "--output_dir", app.config['UPLOAD_FOLDER']
            ]
            print(f"Running command: {' '.join(command)}")
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"✅ Whisper CLI finished. VTT file should be at {vtt_filepath}")

            # 3. Read the content of the VTT file created by Whisper
            with open(vtt_filepath, 'r', encoding='utf-8') as f:
                vtt_content = f.read()

            # 4. Return the VTT content in the response
            return Response(
                vtt_content,
                mimetype="text/vtt",
                headers={"Content-Disposition": "attachment; filename=transcription.vtt"}
            )

        except subprocess.CalledProcessError as e:
            # This will catch errors if the whisper command fails
            print(f"Error during Whisper CLI execution: {e.stderr}")
            return jsonify({"error": "Transcription failed.", "details": e.stderr}), 500
        except FileNotFoundError:
            # This catches the error if the VTT file wasn't created
             print(f"Error: VTT file not found at {vtt_filepath}")
             return jsonify({"error": "Transcription output file not found."}), 500
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return jsonify({"error": "An unexpected error occurred."}), 500
        finally:
            # 5. Clean up both the audio and the VTT file
            if os.path.exists(audio_filepath):
                os.remove(audio_filepath)
            if os.path.exists(vtt_filepath):
                os.remove(vtt_filepath)
    else:
        return jsonify({"error": f"Invalid file type."}), 400

# --- Run the App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)