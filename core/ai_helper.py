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
    def generate_individual_agenda(self, reports_text: str) -> str:
        """为单人生成议程总结"""
        system_prompt = (
            "你是资深 HRBP 专家，正在为该BP梳理其本周的核心议程重点。\n"
            "请根据该BP填写的周报（含勾选的重点），简短归纳：\n"
            "1. 核心需要探讨的卡点与事项\n"
            "2. 潜在的业务或人员风险预警（如有）\n"
            "输出语言干练、直指核心，总字数限制在 60-100 字，无需客套寒暄。"
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": reports_text},
                ],
                max_tokens=200,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"个人议程生成失败: {e}"

    def summarize_global_agenda(self, all_agendas_text: str) -> str:
        system_prompt = (
            "你是资深 HR 负责人，正在为即将召开的团队周会提取全局视角的议程指导。\n"
            "用户提供的是本组各BP个人的AI议程总结，请以“总-分”的排版结构输出汇总提炼：\n"
            "首先用一两句话总结本组目前的全局共性问题、核心风险或整体趋势，提醒负责人关注。\n"
            "然后在下方另起一段或使用列表，点名到个人，具体指出谁的哪个模块存在卡点/风险（例如：@某某：三区出现集中离职风险等）。\n"
            "请保持专业、精炼，过渡自然，**一定不要在此回复中生硬地出现“【总】”或“【分】”这几个字**。"
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": all_agendas_text},
                ],
                max_tokens=400,
                temperature=0.4,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"全局汇总分析失败: {e}"


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
