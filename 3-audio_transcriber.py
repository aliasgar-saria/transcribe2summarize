import os
import json
from datetime import datetime
import whisper
import torch

class AudioTranscriber:
    def __init__(self, audio_folder='aac', output_folder='transcripts', 
                 model_size='small'):
        self.audio_folder = audio_folder
        self.output_folder = output_folder
        self.tracking_file = os.path.join(output_folder, 'transcribed_files.json')
        
        # Create necessary directories
        os.makedirs(self.audio_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Load processed files tracking
        self.processed_files = self._load_processed_files()
        
        # Set device
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        
        # Load the model safely
        try:
            print("Loading Whisper model...")
            # Add Whisper model classes to safe globals
            torch.serialization.add_safe_globals([whisper.model.Whisper])
            
            # Load model with weights_only=True
            self.model = whisper.load_model(
                model_size,
                device=self.device,
                download_root=os.path.join(os.getcwd(), "whisper_model")
            )
            print("Model loaded successfully")
        except Exception as e:
            raise Exception(f"Error loading model: {str(e)}")

    # Rest of your class implementation remains the same...

    def _load_processed_files(self):
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'r') as f:
                return json.load(f)
        return {}

    def _update_processed_files(self, filename):
        self.processed_files[filename] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.tracking_file, 'w') as f:
            json.dump(self.processed_files, f, indent=4)

    def transcribe_files(self):
        audio_files = [f for f in os.listdir(self.audio_folder) 
                      if f.lower().endswith(('.aac', '.mp3', '.wav', '.m4a'))]

        if not audio_files:
            print("No audio files found in the input folder")
            return

        for audio_file in audio_files:
            if audio_file in self.processed_files:
                print(f"Skipping {audio_file} - already transcribed on "
                      f"{self.processed_files[audio_file]}")
                continue

            try:
                print(f"\nTranscribing {audio_file}...")
                audio_path = os.path.join(self.audio_folder, audio_file)
                output_path = os.path.join(
                    self.output_folder, 
                    os.path.splitext(audio_file)[0] + '.txt'
                )

                # Perform transcription
                result = self.model.transcribe(
                    audio_path,
                    language="en",
                    fp16=False  # Use False if you don't have GPU
                )

                # Write transcription to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    if 'segments' in result:
                        for segment in result['segments']:
                            f.write(f"[{segment['start']:.2f}s -> {segment['end']:.2f}s] "
                                   f"{segment['text']}\n")
                    else:
                        f.write(result['text'])

                self._update_processed_files(audio_file)
                print(f"Successfully transcribed {audio_file}")

            except Exception as e:
                print(f"Error processing {audio_file}: {str(e)}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                continue

def main():
    try:
        transcriber = AudioTranscriber(
            audio_folder='aac',
            output_folder='transcripts',
            model_size='small'
        )
        transcriber.transcribe_files()
        
    except KeyboardInterrupt:
        print("\nTranscription interrupted by user")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")

if __name__ == "__main__":
    main()