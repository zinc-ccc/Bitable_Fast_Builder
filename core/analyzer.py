import yaml
import os
from openai import OpenAI

class Analyzer:
    def __init__(self, config_path="configs/config.yaml", prompt_path="prompts/analyzer.md"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
            
        self.client = OpenAI(
            api_key=self.config['openai']['api_key'],
            base_url=self.config['openai']['base_url']
        )

    def analyze_requirement(self, user_input: str):
        """
        调用 LLM 分析用户的自然语言描述，并返回结构化的表设计。
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config['openai']['model'],
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_input}
                ],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"AI Analysis failed: {e}")
            return None

if __name__ == "__main__":
    # 简单测试逻辑
    pass
