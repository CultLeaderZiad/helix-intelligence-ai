import json
import datetime
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from app.schemas.analysis import Insight, Pattern
from app.schemas.creative import Creative

class AIProvider(ABC):
    @abstractmethod
    async def _call_api(self, messages: List[dict]) -> str:
        """Subclasses implement this to call their respective API"""
        pass

    async def generate_insight(self, creative: Creative, context: str = "") -> Insight:
        """Generate an insight for a specific creative"""
        prompt = f"""
        Analyze this creative and provide a single actionable insight.
        Creative details:
        Headline: {creative.headline}
        Body: {creative.body}
        Format: {creative.format}
        Platform: {creative.platform}
        
        {context}
        
        Return a JSON object with:
        - kind: 'opportunity', 'warning', or 'observation'
        - title: Short descriptive title
        - summary: 1-2 sentence explanation
        - confidence: Float between 0.0 and 1.0
        """
        
        result_text = await self._call_api([
            {"role": "system", "content": "You are a direct, concise marketing analyst. Always reply with valid JSON only."},
            {"role": "user", "content": prompt}
        ])
        
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(result_text)
            return Insight(
                id=f"insight_{datetime.datetime.now().timestamp()}",
                creative_id=creative.id,
                kind=data.get("kind", "opportunity"),
                title=data.get("title", "Generated Insight"),
                summary=data.get("summary", "Analysis completed."),
                confidence=float(data.get("confidence", 0.8)),
                evidence_creative_ids=[creative.id],
                model_version=getattr(self, "model", "unknown"),
                generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
            )
        except Exception as e:
            raise Exception(f"Failed to parse AI response: {e}\nResponse: {result_text}")
        
    async def generate_patterns(self, creatives: List[Creative]) -> List[Pattern]:
        """Extract patterns across multiple creatives"""
        prompt = "Identify 2 common patterns across these creatives:\n\n"
        for i, c in enumerate(creatives):
            prompt += f"Creative {i+1}: {c.headline} | {c.body}\n"
            
        prompt += """\nReturn a JSON array of objects, each with:
        - label: Short name (e.g., 'Fast Paced Cuts')
        - family: 'visual', 'copy', or 'structural'
        - prevalence: Float between 0.0 and 1.0
        - lift_index: Float indicating performance lift (e.g. 1.25 for 25% lift)
        """
        
        result_text = await self._call_api([
            {"role": "system", "content": "You are a marketing analyst. Always reply with valid JSON array only."},
            {"role": "user", "content": prompt}
        ])
        
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
                
            data = json.loads(result_text)
            
            # Handle both direct list and dict with list property (e.g. {"patterns": [...]})
            if isinstance(data, dict):
                items = data.get("patterns") or data.get("data") or data.get("results")
                if not items:
                    for v in data.values():
                        if isinstance(v, list):
                            items = v
                            break
                if not items:
                    items = [data]
            elif isinstance(data, list):
                items = data
            else:
                items = []

            patterns = []
            for item in items:
                if isinstance(item, dict):
                    patterns.append(Pattern(
                        id=f"pattern_{datetime.datetime.now().timestamp()}_{len(patterns)}",
                        label=item.get("label") or item.get("name", "Pattern"),
                        family=item.get("family", "structural"),
                        prevalence=float(item.get("prevalence", 0.5)),
                        lift_index=float(item.get("lift_index", 1.0))
                    ))
            return patterns
        except Exception as e:
            raise Exception(f"Failed to parse AI response: {e}\nResponse: {result_text}")
