import google.generativeai as genai
from typing import List, Dict, Optional
import os

class GeminiChat:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self.chat = None
        self.context = ""
        self.use_mock = False
        
        if api_key and api_key != "AIzaSyDVWb3Jgw3BI2AFmhZzE-WUhfAcn9I2kUE":
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                print("✅ Gemini model loaded")
            except Exception as e:
                print(f"⚠️ Error loading Gemini: {e}")
                self.use_mock = True
        else:
            print("⚠️ No Gemini API key found, using mock mode")
            self.use_mock = True
    
    def set_context(self, transcript: str, summary: str, video_info: Dict, key_points: List[str]):
        """Set the context for the chat"""
        
        self.context = f"""
        You are an AI assistant that helps users understand video content.
        
        VIDEO INFORMATION:
        -----------------
        Title: {video_info.get('original_name', 'Unknown')}
        Duration: {video_info.get('duration', 0)} seconds
        
        TRANSCRIPT:
        ----------
        {transcript[:2000]}...
        
        SUMMARY:
        -------
        {summary}
        
        KEY POINTS:
        ----------
        {', '.join(key_points[:10])}
        
        Instructions:
        1. Answer questions based ONLY on the video content provided above
        2. If the question is not related to the video, politely say you can only answer video-related questions
        3. Provide detailed, accurate answers
        4. Be helpful and conversational
        """
        
        if not self.use_mock and self.model:
            try:
                self.chat = self.model.start_chat(history=[])
                self.chat.send_message(self.context)
            except Exception as e:
                print(f"Error starting chat: {e}")
                self.use_mock = True
    
    async def ask_question(self, question: str) -> str:
        """Ask a question about the video content"""
        
        # Mock mode for testing
        if self.use_mock or self.chat is None:
            return self._get_mock_response(question)
        
        try:
            response = self.chat.send_message(question)
            return response.text
        except Exception as e:
            print(f"Chat error: {e}")
            return f"I'm having trouble answering that right now. Error: {str(e)}"
    
    def _get_mock_response(self, question: str) -> str:
        """Get mock response for testing"""
        
        question_lower = question.lower()
        
        if "summary" in question_lower or "what is the video about" in question_lower:
            return "Based on the video transcript, it appears to be about AI technology and its applications in video processing and summarization."
        
        elif "duration" in question_lower or "how long" in question_lower:
            return "The video duration information would be shown here once processed."
        
        elif "key points" in question_lower or "main ideas" in question_lower:
            return "The main points from this video include: 1) AI applications in video processing, 2) Transcription techniques, 3) Summarization methods."
        
        elif "language" in question_lower:
            return "The video appears to be in English."
        
        elif "thank" in question_lower:
            return "You're welcome! Feel free to ask if you have more questions about the video."
        
        else:
            return "I understand your question about the video. However, I'd need more specific information from the video content to provide a detailed answer. Could you please rephrase or ask about something specific from the video?"