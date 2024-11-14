import asyncio
import edge_tts
import json
import os
from pathlib import Path
from datetime import datetime

# Constants
VOICE = "en-US-JennyNeural"
SUMMARY_DIR = "summaries"
AUDIO_DIR = "summaryaudio"
RATE = "+1%"
VOLUME = "+0%"

def load_audio_status(summary_dir):
    """Load the audio conversion tracking JSON file or create if not exists."""
    tracking_file = Path(summary_dir) / "summary_audio_status.json"
    if tracking_file.exists():
        with open(tracking_file, 'r') as f:
            return json.load(f)
    return {"completed_conversions": {}}

def save_audio_status(summary_dir, status_data):
    """Save the audio conversion status to JSON file."""
    tracking_file = Path(summary_dir) / "summary_audio_status.json"
    with open(tracking_file, 'w') as f:
        json.dump(status_data, f, indent=4)

async def convert_text_to_speech(text, output_file, voice=VOICE):
    """Convert text to speech using edge-tts."""
    try:
        communicate = edge_tts.Communicate(text, voice, rate=RATE, volume=VOLUME)
        await communicate.save(output_file)
        return True
    except Exception as e:
        print(f"Error converting text to speech: {str(e)}")
        return False

async def process_summary_files():
    """Process all summary files and convert them to audio."""
    # Create output directory if it doesn't exist
    audio_dir = Path(AUDIO_DIR)
    audio_dir.mkdir(exist_ok=True)
    
    # Get the summaries directory
    summaries_dir = Path(SUMMARY_DIR)
    if not summaries_dir.exists():
        print("Error: 'summaries' directory not found!")
        return
    
    # Load tracking status from summaries directory
    status_data = load_audio_status(summaries_dir)
    
    # Process each summary file
    for summary_file in summaries_dir.glob('*.txt'):
        try:
            file_path = str(summary_file)
            file_stats = os.stat(file_path)
            
            # Skip if file was already processed and hasn't been modified
            if (file_path in status_data["completed_conversions"] and 
                status_data["completed_conversions"][file_path]["mtime"] == file_stats.st_mtime):
                print(f"Skipping already processed file: {summary_file.name}")
                continue
            
            # Read the summary text
            with open(summary_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Create output filename
            output_filename = audio_dir / f"{summary_file.stem}.mp3"
            
            print(f"Converting {summary_file.name} to audio...")
            
            # Convert to speech
            success = await convert_text_to_speech(
                text=text,
                output_file=str(output_filename)
            )
            
            if success:
                # Update status data
                status_data["completed_conversions"][file_path] = {
                    "mtime": file_stats.st_mtime,
                    "processed_date": datetime.now().isoformat(),
                    "audio_path": str(output_filename),
                    "summary_file": summary_file.name,
                    "voice_used": VOICE,
                    "rate": RATE,
                    "volume": VOLUME
                }
                
                # Save updated status in summaries directory
                save_audio_status(summaries_dir, status_data)
                
                print(f"✓ Created audio file: {output_filename.name}")
            else:
                print(f"✗ Failed to create audio for: {summary_file.name}")
                
        except Exception as e:
            print(f"Error processing {summary_file.name}: {str(e)}")

def main():
    """Main function to run the text-to-speech conversion."""
    try:
        # Run the async process
        loop = asyncio.get_event_loop_policy().get_event_loop()
        try:
            loop.run_until_complete(process_summary_files())
        finally:
            loop.close()
            
    except Exception as e:
        print(f"Error in main process: {str(e)}")

if __name__ == "__main__":
    main()