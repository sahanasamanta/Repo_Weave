import json
import boto3
import os
import re
from typing import List, Dict, Any

class BedrockHelper:
    def __init__(self):
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')  # Changed default
        self.enabled = os.environ.get('BEDROCK_ENABLED', 'false').lower() == 'true'

    def generate_fixes(self, issues: List[str], repo_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered fixes for detected issues using Bedrock
        """
        if not self.enabled or not issues:
            return {"enabled": False, "suggestions": []}

        try:
            # Prepare the prompt
            prompt = self._build_prompt(issues, repo_summary)
            
            print(f"Calling Bedrock with {len(issues)} issues...")
            
            # Call Bedrock with Nova format (FIXED)
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ],
                    "inferenceConfig": {
                        "max_new_tokens": 2000,
                        "temperature": 0.7,
                        "topP": 0.9
                    }
                })
            )
            
            # Parse response (FIXED for Nova)
            response_body = json.loads(response['body'].read())
            suggestions = self._parse_response(response_body)
            
            print(f"Bedrock generated {len(suggestions)} suggestions")
            
            return {
                "enabled": True,
                "model": self.model_id,
                "suggestions": suggestions,
                "issues_analyzed": len(issues)
            }
            
        except Exception as e:
            print(f"Bedrock error: {str(e)}")
            return {
                "enabled": True,
                "error": str(e),
                "suggestions": []
            }

    def _build_prompt(self, issues: List[str], summary: Dict[str, Any]) -> str:
        """Build a SIMPLER prompt for Nova Pro"""
        # Take first 5 issues to keep it simple
        sample_issues = issues[:5]
        
        prompt = f"""You are a Python expert. Here are issues found in a code repository:

{chr(10).join([f'- {issue}' for issue in sample_issues])}

For each issue, provide a fix in this exact JSON format:
{{
    "fixes": [
        {{
            "issue": "the exact issue",
            "explanation": "what's wrong and how to fix it",
            "code_example": "example code showing the fix"
        }}
    ]
}}

Return ONLY the JSON, no other text."""
        return prompt

    def _parse_response(self, response_body: Dict[str, Any]) -> List[Dict[str, str]]:
        """Parse Nova Pro response into structured fixes (FIXED)"""
        try:
            # Nova returns output in 'output' field
            if 'output' in response_body:
                message = response_body['output'].get('message', {})
                content = message.get('content', [])
                if content and len(content) > 0:
                    text = content[0].get('text', '')
                else:
                    return []
            else:
                return []
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                fixes_data = json.loads(json_match.group())
                return fixes_data.get('fixes', [])
            return []
            
        except Exception as e:
            print(f"Error parsing Bedrock response: {e}")
            return []