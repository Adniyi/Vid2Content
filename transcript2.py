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
import mimetypes
import re


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
        self.audio_path = None


    def sanitize_filename(self, filename):
        # Replace invalid characters with an underscore
        return re.sub(r'[<>:"/\\|?*]', '', filename)
    
    
    def download_youtube_video(self, video_url):
        if self.audio_path and os.path.exists(self.audio_path):
            return self.audio_path
        try:
            with yt_dlp.YoutubeDL({'quiet':True}) as ydl:
               info_dict = ydl.extract_info(video_url, download=False)
               title = info_dict.get('title', 'audio').replace(' ', '_')

            # Sanitize the filename before download
            sanitized_title = self.sanitize_filename(title)
            audio_filename = f"./static/uploads/{sanitized_title}.mp3"

            if os.path.exists(audio_filename):
               print(f"Audio already exits: {audio_filename}") 
               return audio_filename
           
            ydl_opts = {
                'format': 'bestaudio/best',
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '0',  # best
                'outtmpl': audio_filename,
                'quiet': False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            print(f"Audio downloaded: {audio_filename}")
            self.audio_path = audio_filename
            return audio_filename
           
        except Exception as e:
           print(f"Error Downloading video: {e}")
           return None



    def transcribe_video_with_assemblyai(self,audio_path):

        # Step3: transcription job on AssemblyAI
        transcript = aai.Transcriber()
        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.slam_1)
        result = transcript.transcribe(audio_path,config)

        if result.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {result.error}")

        # Poll until transcription is complete
        # while result.status != 'completed':
        #     result = transcript.get_result(result.id)
        
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
