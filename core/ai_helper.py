"""
ai_helper.py
============
DeepSeek (OpenAI-compatible) 接口封装。
同时支持本地 configs/config.yaml 和 Streamlit Cloud st.secrets 读取凭证。
"""
import os
import yaml
from openai import OpenAI


def _load_config():
    """优先从 Streamlit secrets 读取，回退到本地 config.yaml。"""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "openai" in st.secrets:
            return {
                "api_key":  st.secrets["openai"]["api_key"],
                "base_url": st.secrets["openai"].get("base_url", "https://api.deepseek.com"),
                "model":    st.secrets["openai"].get("model", "deepseek-chat"),
            }
    except Exception:
        pass

    # 回退：本地 config.yaml
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    oa = cfg.get("openai", {})
    return {
        "api_key":  oa.get("api_key", ""),
        "base_url": oa.get("base_url", "https://api.deepseek.com"),
        "model":    oa.get("model", "deepseek-chat"),
    }


# ────────────────────────────────────────────────────────
# 提示词
# ────────────────────────────────────────────────────────
_AGENDA_PROMPT = (
    "你是一位专业的HRBP负责人助理。请根据以下各BP提交的周报摘要，"
    "总结出一份【本周汇报议程建议】。关注重点抓取、异常反馈和竞对动态，"
    "输出简明扼要的几条待参会讨论事项。字数控制在200字以内。"
)

_MODULE_SUMMARY_PROMPT = (
    "你是资深HR管理助理。请将以下HRBP填写的模块内容提炼为一句结论。\n"
    "要求：\n"
    "- 严格控制在15-20字（内容极少时可更短，不强行凑字）\n"
    "- 禁止使用'本周'、'完成了'、'进行了'等空泛套话\n"
    "- 直接说结论，不加任何前缀或解释\n"
    "- 只输出那一句话"
)


class AIHelper:
    def __init__(self):
        cfg = _load_config()
        self.model = cfg["model"]
        self.client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])

    # ── 议程生成（基于摘要文本）────────────────────────
    def generate_agenda(self, reports_text: str) -> str:
        if not reports_text.strip():
            return "暂无汇报内容"
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _AGENDA_PROMPT},
                    {"role": "user",   "content": reports_text},
                ],
                max_tokens=300,
                temperature=0.4,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"AI 议程生成失败: {e}"

    # ── 议程生成（基于原始内容，含风险分析）───────────
    def generate_agenda_from_raw(self, raw_reports_text: str) -> str:
        """
        基于 BP 填写的原始内容（非摘要）生成综合议程建议。
        包含：风险识别、未勾选重点但值得关注的模块、跨 BP 共性问题。
        """
        if not raw_reports_text.strip():
            return "暂无原始汇报内容"
        system_prompt = (
            "你是资深 HRBP 管理顾问，正在为负责人准备周会议程。\n"
            "请阅读以下各 BP 提交的周报原始内容（含BP勾选的重点模块），完成以下分析：\n"
            "1. 【风险预警】识别潜在的人员流失风险、业务异常、招聘卡点等\n"
            "2. 【遗漏关注】找出哪些BP未勾选为重点汇报，但内容显示需要关注的模块\n"
            "3. 【共性议题】提炼多个BP共同提到的问题或趋势\n"
            "4. 【议程建议】给出3-5条本周会议重点讨论项\n"
            "输出格式：每部分分段，语言简洁专业，总字数200字以内。"
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": raw_reports_text},
                ],
                max_tokens=400,
                temperature=0.4,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"AI 议程分析失败: {e}"


    # ── 单模块摘要 ───────────────────────────────────
    def summarize_module(self, module_name: str, raw_content: str) -> str:
        """
        对单个模块的原始内容生成 15-20 字精简摘要。
        - raw_content 为空或极短（<8字）→ 返回 "" 不调用 API
        """
        if not raw_content or len(raw_content.strip()) < 8:
            return ""
        try:
            user_msg = f"【{module_name}】\n{raw_content.strip()}"
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _MODULE_SUMMARY_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                max_tokens=60,
                temperature=0.3,
            )
            summary = resp.choices[0].message.content.strip()
            print(f"  [AI摘要] {module_name}: {summary}")
            return summary
        except Exception as e:
            print(f"  [AI摘要] {module_name} 调用失败: {e}")
            return ""
