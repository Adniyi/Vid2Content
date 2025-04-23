import assemblyai as aai
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from transformers import DistilBertTokenizer, DistilBertModel
import torch
import numpy as np
from dotenv import load_dotenv
import os
from pytube import YouTube
import yt_dlp


load_dotenv()

class Transcript:
    def __init__(self, url:str):
        self.url = url
        # Initialize spaCy for keyword extraction (optional for extra processing)
        self.nlp = spacy.load("en_core_web_sm")

        # AssemblyAI setup
        aai.settings.api_key = os.getenv("ASSEMBLY_AI_API_KEY")


        # DistilBERT Setup (Lighter and Faster version of BERT)
        self.tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
        self.distilbert_model = DistilBertModel.from_pretrained('distilbert-base-uncased')


    def download_youtube_video(self, video_url):
        # Download video using pytube
        # yt = YouTube(video_url)
        # Alternatively well use yt_dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,  # Extract audio only
            'audioquality': 1,  # Best audio quality
            'outtmpl': 'static/uploads/audio.mp3',  # Save as MP3
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=True)
                audio_path = ydl.prepare_filename(info_dict)
                print(audio_path)
                return audio_path
            # video_stream = yt.streams.filter(only_audio=True).first()
            # print(video_stream)
        
            # # Ensures directiory exits
            # output_path = "static/uploads/"
            # os.makedirs(output_path, exist_ok=True)

            # # Create audio path 
            # os.path.join(output_path, 'audio.mp3')

            # # Only download if the file does not exits
            # audio_path = video_stream.download(output_path=output_path,filename='audio.mp3')
            
            # return audio_path
        except Exception as e:
            # print(f"Error downloading audio: {e}")
            print(f"Error downloading video with yt-dlp: {e}")
        
    
    def upload_audio_url(self,audio_path):
        # turn the audio path to a url
        transcriber = aai.Transcriber()
        upload_url = transcriber.upload_file(audio_path)
        return upload_url

    def transcribe_video_with_assemblyai(self,video_url):
        # Step1: Download the youtube video
        audio_path = self.download_youtube_video(video_url=video_url)

        # Step2: Upload the audio file to assembly ai
        upload_url = self.upload_audio_url(audio_path=audio_path)
        print(f"[DEBUG]: Uploaded audio file {upload_url}")

        # Step3: transcription job on AssemblyAI
        transcript = aai.Transcriber()
        result = transcript.transcribe(upload_url)

        if result.status == 'error':
            raise Exception(f"Transcription failed: {result.error}")

        # Poll until transcription is complete
        while result.status != 'completed':
            result = transcript.get_result(result.id)
        
        return result.text
    
    def extract_tfidf_keywords(self, transcript):
    # Tokenize and compute the TF-IDF scores for each word
        tfidf_vectorizer = TfidfVectorizer(stop_words='english', max_features=10)
        tfidf_matrix = tfidf_vectorizer.fit_transform([transcript])
        feature_names = np.array(tfidf_vectorizer.get_feature_names_out())
        
        # Get the top TF-IDF terms
        scores = tfidf_matrix.toarray()[0]
        top_indices = scores.argsort()[::-1][:10]
        top_keywords = feature_names[top_indices]

        
        return top_keywords.tolist()
    
    def extract_distilbert_keywords(self, transcript):
    # Tokenize the input transcript using DistilBERT tokenizer
        inputs = self.tokenizer(transcript, return_tensors='pt', max_length=512, truncation=True)
        
        # Get DistilBERT embeddings
        with torch.no_grad():
            outputs = self.distilbert_model(**inputs)
        
        # Get the embeddings of the [CLS] token, representing the entire sentence
        cls_embeddings = outputs.last_hidden_state[:, 0, :].squeeze().numpy()

        # Compute cosine similarity between all words and the document embedding ([CLS] token)
        word_embeddings = outputs.last_hidden_state.squeeze().numpy()
        cosine_similarities = np.array([np.dot(cls_embeddings, word_embedding) / (np.linalg.norm(cls_embeddings) * np.linalg.norm(word_embedding)) for word_embedding in word_embeddings])
        
        # Get the indices of the most relevant words (top 10)
        sorted_idx = np.argsort(cosine_similarities)[::-1][:10]
        tokens = self.tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
        
        # Extract top keywords from tokens
        top_keywords = [tokens[i] for i in sorted_idx if tokens[i] not in ['[CLS]', '[SEP]'] and not tokens[i].startswith('##')][:10]
        
        return top_keywords
    
    def get_combined_keywords(self, transcript, max_keywords=10):
        """
        Combine TF-IDF and DistilBERT keywords with smart logic:
        - Common keywords come first
        - Then fill in the rest from both lists
        """

        tfidf_keywords = self.extract_tfidf_keywords(transcript)
        distilbert_keywords = self.extract_distilbert_keywords(transcript)

        # Normalize to lowercase to avoid duplicates
        tfidf_set = set([kw.lower() for kw in tfidf_keywords])
        distilbert_set = set([kw.lower() for kw in distilbert_keywords])

        # Common terms first
        common = list(tfidf_set & distilbert_set)

        # Unique terms from each
        tfidf_only = list(tfidf_set - distilbert_set)
        distilbert_only = list(distilbert_set - tfidf_set)

        # Combine and trim
        combined = common + tfidf_only + distilbert_only
        return combined[:max_keywords]
