from moviepy.editor import VideoFileClip, AudioFileClip
import os
import gc
import json
from datetime import datetime

class MediaConverter:
    def __init__(self, input_folder='media', output_folder='aac', chunk_size=1024*1024):
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.chunk_size = chunk_size
        self.tracking_file = os.path.join(input_folder, 'processed_files.json')
        self.processed_files = self._load_processed_files()
        
        # Supported file extensions
        self.video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv')
        self.audio_extensions = ('.mp3', '.wav', '.m4a', '.wma', '.ogg', '.flac')

    def _load_processed_files(self):
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'r') as f:
                return json.load(f)
        return {}

    def _update_processed_files(self, filename):
        self.processed_files[filename] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.tracking_file, 'w') as f:
            json.dump(self.processed_files, f, indent=4)

    def _is_video_file(self, filename):
        return filename.lower().endswith(self.video_extensions)

    def _is_audio_file(self, filename):
        return filename.lower().endswith(self.audio_extensions)

    def convert_media(self):
        # Create output folder if it doesn't exist
        os.makedirs(self.output_folder, exist_ok=True)

        # Get list of media files
        media_files = [f for f in os.listdir(self.input_folder) 
                      if self._is_video_file(f) or self._is_audio_file(f)]

        if not media_files:
            print("No media files found in the input folder")
            return

        for media_file in media_files:
            # Skip if already processed
            if media_file in self.processed_files:
                print(f"Skipping {media_file} - already processed on {self.processed_files[media_file]}")
                continue

            try:
                print(f"\nProcessing {media_file}...")
                media_path = os.path.join(self.input_folder, media_file)
                audio_path = os.path.join(self.output_folder, 
                                        os.path.splitext(media_file)[0] + '.aac')

                # Process media with memory optimization
                media = None
                try:
                    # Load media file based on type
                    if self._is_video_file(media_file):
                        media = VideoFileClip(media_path, audio_buffersize=self.chunk_size)
                        audio = media.audio
                    else:
                        media = AudioFileClip(media_path)
                        audio = media
                    
                    # Extract/convert audio with optimized settings
                    audio.write_audiofile(
                        audio_path,
                        codec='aac',
                        fps=44100,  # Standard audio sampling rate
                        nbytes=2,   # 16-bit audio
                        buffersize=self.chunk_size,
                        verbose=False,
                        logger=None
                    )
                    
                    # Update tracking file
                    self._update_processed_files(media_file)
                    print(f"Successfully converted {media_file} to AAC")

                except Exception as e:
                    print(f"Error processing {media_file}: {str(e)}")
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                
                finally:
                    # Clean up resources
                    if media is not None:
                        media.close()
                        del media
                    gc.collect()  # Force garbage collection

            except Exception as e:
                print(f"Fatal error with {media_file}: {str(e)}")
                continue

def main():
    # Initialize converter with memory-efficient settings
    chunk_size = 1024 * 1024  # 1MB chunks
    converter = MediaConverter(chunk_size=chunk_size)
    
    try:
        converter.convert_media()
    except KeyboardInterrupt:
        print("\nConversion interrupted by user")
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
    finally:
        gc.collect()

if __name__ == "__main__":
    main()