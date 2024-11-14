import os
import json
from pathlib import Path
from ollama import Client
from datetime import datetime

# Constants
MAX_CHUNK_SIZE = 1800
TRANSCRIPT_TRACKING_FILE = "transcript_status.json"

def load_transcript_status(transcript_dir):
    """Load the transcript tracking JSON file or create if not exists."""
    status_file = transcript_dir / TRANSCRIPT_TRACKING_FILE
    if status_file.exists():
        with open(status_file, 'r') as f:
            return json.load(f)
    return {"completed_transcripts": {}}

def save_transcript_status(transcript_dir, status_data):
    """Save the transcript status to JSON file."""
    status_file = transcript_dir / TRANSCRIPT_TRACKING_FILE
    with open(status_file, 'w') as f:
        json.dump(status_data, f, indent=4)

def summarize_chunk(client, chunk):
    """Summarize a single chunk of text with enhanced prompt for detailed analysis."""
    prompt = f"""As an expert analyst, provide a detailed and structured summary of this transcript segment. Focus on creating a comprehensive narrative that captures:

CONTEXT & STRUCTURE:
- Identify the format (lecture, audiobook, podcast, discussion)
- Note speaking style, tone, and delivery method
- Capture the flow and progression of ideas

KEY ELEMENTS TO ANALYZE:
- Main topics and core arguments presented
- Supporting evidence and examples given
- Technical terms or specialized concepts explained
- Notable quotes or significant statements
- Questions raised and answers provided
- Any debates or contrasting viewpoints
- Real-world applications or case studies mentioned

ENSURE TO INCLUDE:
- Chronological progression of the discussion
- Relationships between different topics
- Practical takeaways or actionable insights
- Complex concepts broken down into understandable parts

Here's the transcript segment to analyze:

{chunk}

Provide a thorough summary that:
1. Maintains the original depth and complexity
2. Uses clear topic transitions
3. Preserves important details and examples
4. Captures the educational or informative value
5. Reflects the speaker's expertise and perspective"""
    
    response = client.generate(
        model='smollm2:360m',
        prompt=prompt,
        options={
            'temperature': 0.3,  # Reduced for more focused output
            'top_p': 0.92,
            'max_tokens': 500,   # Increased for more detailed summaries
            'presence_penalty': 0.3,  # Encourage diverse content
            'frequency_penalty': 0.3  # Reduce repetition
        }
    )
    
    return response['response']
def create_chunks(text, max_chunk_size=MAX_CHUNK_SIZE):
    """
    Create chunks of text while preserving sentence integrity and context.
    
    Args:
        text (str): The input text to be chunked
        max_chunk_size (int): Maximum size of each chunk in characters
        
    Returns:
        list: List of text chunks
    """
    # Split text into sentences (basic splitting by common sentence endings)
    sentences = []
    current_sentence = []
    
    # Split by words but preserve punctuation
    words = text.replace('\n', ' ').split(' ')
    
    for word in words:
        current_sentence.append(word)
        # Check for sentence endings
        if word.strip().endswith(('.', '!', '?', '..."', '."', '!"', '?"')):
            sentences.append(' '.join(current_sentence))
            current_sentence = []
    
    # Add any remaining words as a sentence
    if current_sentence:
        sentences.append(' '.join(current_sentence))
    
    # Create chunks from sentences
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        sentence_length = len(sentence) + 1  # +1 for space
        
        # If adding this sentence would exceed max_chunk_size
        if current_length + sentence_length > max_chunk_size and current_chunk:
            # Save current chunk and start a new one
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_length = 0
        
        # Add sentence to current chunk
        current_chunk.append(sentence)
        current_length += sentence_length
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Handle case where a single sentence is longer than max_chunk_size
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > max_chunk_size:
            # Split long chunks by words while trying to preserve context
            words = chunk.split()
            temp_chunk = []
            temp_length = 0
            
            for word in words:
                word_length = len(word) + 1  # +1 for space
                if temp_length + word_length > max_chunk_size and temp_chunk:
                    final_chunks.append(' '.join(temp_chunk))
                    temp_chunk = []
                    temp_length = 0
                temp_chunk.append(word)
                temp_length += word_length
            
            if temp_chunk:
                final_chunks.append(' '.join(temp_chunk))
        else:
            final_chunks.append(chunk)
    
    return final_chunks

def process_transcript(client, transcript_path):
    """Process a single transcript file with enhanced summary compilation."""
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        chunks = create_chunks(text)
        chunk_summaries = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}")
            summary = summarize_chunk(client, chunk)
            chunk_summaries.append(summary)
        
        if len(chunk_summaries) > 1:
            # Enhanced final summary prompt for combining chunks
            final_prompt = f"""Create a cohesive and comprehensive final summary of this entire transcript. 
            
The content appears to be divided into several segments. Synthesize these into a well-structured analysis that:

1. Opens with an overview of the entire content
2. Maintains chronological and logical flow
3. Highlights the progression of ideas
4. Preserves critical details and examples
5. Connects related concepts across segments
6. Concludes with key takeaways

Here are the segment summaries to combine:

{' '.join(chunk_summaries)}

Provide a detailed final summary that captures the full scope and depth of the content while maintaining clarity and coherence."""

            response = client.generate(
                model='smollm2:360m',
                prompt=final_prompt,
                options={
                    'temperature': 0.3,
                    'top_p': 0.92,
                    'max_tokens': 800,  # Increased for comprehensive final summary
                    'presence_penalty': 0.3,
                    'frequency_penalty': 0.3
                }
            )
            
            return response['response']
        
        return chunk_summaries[0]
    
    except Exception as e:
        print(f"Error processing {transcript_path}: {str(e)}")
        return None

def main():
    # Setup paths
    base_dir = Path.cwd()
    transcript_dir = base_dir / 'transcripts'
    summary_dir = base_dir / 'summaries'
    summary_dir.mkdir(exist_ok=True)
    
    # Load transcript status
    transcript_status = load_transcript_status(transcript_dir)
    
    # Initialize Ollama client
    client = Client(host='http://localhost:11434')
    
    # Process unprocessed transcript files
    for transcript_file in transcript_dir.glob('*.txt'):
        file_path = str(transcript_file)
        file_stats = os.stat(file_path)
                # Skip if file was already processed and hasn't been modified
        if (file_path in transcript_status["completed_transcripts"] and 
            transcript_status["completed_transcripts"][file_path]["mtime"] == file_stats.st_mtime):
            print(f"Skipping already processed file: {transcript_file.name}")
            continue
            
        print(f"\nProcessing: {transcript_file.name}")
        
        summary = process_transcript(client, transcript_file)
        if summary:
            # Save summary
            summary_path = summary_dir / f'summary_{transcript_file.name}'
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)
                
            # Update transcript status
            transcript_status["completed_transcripts"][file_path] = {
                "mtime": file_stats.st_mtime,
                "processed_date": datetime.now().isoformat(),
                "summary_path": str(summary_path)
            }
            
            # Save transcript status
            save_transcript_status(transcript_dir, transcript_status)
            
            print(f"✓ Summary created: {summary_path.name}")

if __name__ == "__main__":
    main()