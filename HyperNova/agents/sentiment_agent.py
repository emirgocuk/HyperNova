from core.agent import BaseAgent, AgentDecision
from core.llm_service import LLMService
from typing import Dict, Any, List
import requests
import os

class SentimentAgent(BaseAgent):
    """
    Sentiment Agent responsible for analyzing market news and social sentiment.
    Uses CryptoPanic API to fetch headlines and LLM to score them.
    """
    
    def __init__(self):
        super().__init__(name="SentimentAgent")
        # No API Key needed for Google News RSS
        self.llm = LLMService()
        self.last_sentiment_score = 0.0 
        self.last_summary = "Initializing..."

    def fetch_news(self, query="Bitcoin crypto") -> List[str]:
        """
        Fetches latest news headlines from Google News RSS (Free & Real-time).
        """
        # Google News RSS URL for specific query, last 1 hour (when:1h)
        url = f"https://news.google.com/rss/search?q={query}+when:1h&hl=en-US&gl=US&ceid=US:en"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Parse XML simple way to avoid extra dependencies like feedparser
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                # Extract titles from <item> tags
                headlines = []
                count = 0
                for item in root.findall('.//item'):
                    title = item.find('title').text
                    # Clean up Google News source suffix " - SourceName"
                    if " - " in title:
                        title = title.rsplit(" - ", 1)[0]
                    headlines.append(title)
                    count += 1
                    if count >= 5: break
                    
                if not headlines:
                    return ["No recent news found."]
                return headlines
            else:
                return [f"Error fetching news (Status: {response.status_code})"]
                
        except Exception as e:
            print(f"Error fetching news: {e}")
            return ["Error connection to News Source."]

    def analyze(self, market_data: Dict[str, Any], context: Dict[str, Any]) -> AgentDecision:
        """
        Analyses sentiment and returns a decision/score.
        Note: This agent doesn't 'approve/reject' trades directly like RiskManager,
        but provides a 'Sentiment Score' context.
        """
        headlines = self.fetch_news()
        
        # If no real news, return neutral
        if len(headlines) == 1 and "No" in headlines[0]:
            return AgentDecision(approved=True, confidence=0.5, reason="Neutral (No News)", metadata={'score': 0})

        # Ask LLM
        prompt = f"""
        You are a Crypto Sentiment Analyst.
        
        Analyze these news headlines for Bitcoin (BTC):
        {headlines}
        
        Task:
        1. Determine if the overall sentiment is BULLISH, BEARISH, or NEUTRAL.
        2. Assign a score from -1.0 (Extreme Bearish) to +1.0 (Extreme Bullish).
        
        Output Format:
        SCORE: [Number]
        SUMMARY: [One sentence summary]
        """
        
        try:
            response = self.llm.get_response(prompt, system_prompt="Output only the requested format.")
            
            # Parse Response (Simple parsing)
            lines = response.strip().split('\n')
            score = 0.0
            summary = "LLM Analysis"
            
            for line in lines:
                if "SCORE:" in line:
                    score = float(line.replace("SCORE:", "").strip())
                if "SUMMARY:" in line:
                    summary = line.replace("SUMMARY:", "").strip()
            
            self.last_sentiment_score = score
            self.last_summary = summary
            
            # Decision logic: 
            # Approved doesn't mean "Buy", it means "Sentiment Analysis Successful"
            # The 'confidence' can be the absolute score.
            return AgentDecision(
                approved=True, 
                confidence=abs(score), 
                reason=f"Sentiment: {score} ({summary})", 
                metadata={'score': score, 'summary': summary}
            )
            
        except Exception as e:
            return AgentDecision(approved=True, confidence=0.0, reason=f"Sentiment Error: {e}", metadata={'score': 0})
