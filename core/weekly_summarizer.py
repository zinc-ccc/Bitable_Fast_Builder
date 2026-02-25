"""
weekly_summarizer.py
====================
调用 LLM 对新提交的 HRBP 业务周报进行 AI 总结（15-20字），
并将结果回写到多维表的「AI核心要点」字段。

使用方式：
  - 由 run_bot_master.py 在扫描新记录时调用
  - 或直接运行：python -m core.weekly_summarizer
"""

import yaml
import json
from openai import OpenAI

SUMMARY_PROMPT = """你是一位资深 HR 管理顾问的助理。
请阅读以下 HRBP 的周报内容（5个模块），提炼出本周最核心的业务动态或风险点。
输出1句话，严格控制在15-20字之间，禁止使用"本周"、"完成了"等套话，直接说结论。
只输出那一句话，不要任何前缀或解释。"""

class WeeklySummarizer:
    def __init__(self, config_path="configs/config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        
        openai_cfg = cfg.get('openai', {})
        self.client = OpenAI(
            api_key=openai_cfg.get('api_key', ''),
            base_url=openai_cfg.get('base_url', 'https://api.openai.com/v1')
        )
        self.model = openai_cfg.get('model', 'gpt-4')

    def summarize(self, record_fields: dict) -> str:
        """
        传入一条周报记录的字段 dict，返回 AI 总结文本（15-20字）。
        如果调用失败，返回空字符串。
        """
        # 提取 5 个模块内容，过滤掉空值
        module_map = {
            "M1 招聘产出与HC确认": record_fields.get("M1 招聘产出与HC确认", ""),
            "M2 Agent实践与业务进展": record_fields.get("M2 Agent实践与业务进展", ""),
            "M3 人员情况跟进": record_fields.get("M3 人员情况跟进", ""),
            "M4 业务部门情况": record_fields.get("M4 业务部门情况", ""),
            "M5 卡点与下周计划": record_fields.get("M5 卡点与下周计划", ""),
        }
        
        content_parts = []
        for module, text in module_map.items():
            if text and text.strip():
                content_parts.append(f"【{module}】{text.strip()}")
        
        if not content_parts:
            print("  [Summarizer] 所有模块均为空，跳过总结。")
            return ""
        
        user_content = "\n".join(content_parts)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SUMMARY_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=60,
                temperature=0.3
            )
            summary = response.choices[0].message.content.strip()
            print(f"  [Summarizer] AI总结生成: {summary}")
            return summary
        except Exception as e:
            print(f"  [Summarizer] AI调用失败: {e}")
            return ""
