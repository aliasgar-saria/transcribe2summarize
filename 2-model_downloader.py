import os
import whisper
from whisper import _download, _MODELS

class ModelDownloader:
    def __init__(self, model_dir='whisper_model', model_size='small'):
        self.model_dir = model_dir
        self.model_size = model_size
        self.model_path = os.path.join(model_dir, f'{model_size}.pt')
        os.makedirs(model_dir, exist_ok=True)
    
    def download_model(self):
        try:
            print(f"Downloading {self.model_size} model...")
            
            # First ensure the model exists
            if self.model_size not in _MODELS:
                raise ValueError(f"Model {self.model_size} not found. Available models: {whisper.available_models()}")
            
            # Download the model to the specified directory
            if not os.path.exists(self.model_path):
                print(f"Downloading model to {self.model_path}")
                _download(_MODELS[self.model_size], self.model_dir, False)
            
            # Load the model
            model = whisper.load_model(self.model_size)
            print("Model downloaded and loaded successfully")
            return model
            
        except Exception as e:
            raise Exception(f"Error downloading/loading model: {str(e)}")

# Example usage
if __name__ == "__main__":
    downloader = ModelDownloader(model_dir='whisper_model', model_size='small')
    model = downloader.download_model()