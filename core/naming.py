import re

def normalize_field_name(name: str) -> str:
    """
    调整后的命名逻辑：优先美观与简洁。
    1. 将全角符号转为半角。
    2. 优先通过语义重组，其次才是符号替换。
    3. 仅在确实需要分隔时使用冒号 ':'。
    """
    if not name:
        return ""

    # 处理常见全角符号
    name = name.replace('（', '(').replace('）', ')').replace('－', '-').replace('—', '-')
    
    # 如果用户想保留美观，我们不再强制把一切都换成下划线
    # 比如：入职日期(计划) -> 计划入职日期 (这种通常由 AI 在 prompts 里完成)
    
    # 这里的代码兜底逻辑：仅移除/替换掉可能引起 API 解析问题的符号
    name = name.replace('(', ':').replace(')', '')
    name = name.replace('-', '_')
    
    return name.strip()

if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "入职日期(计划)-确认版",
        "岗位唯一码",
        "关联组织-岗位类型",
        "测试（全角）－横线",
    ]
    for case in test_cases:
        print(f"Original: {case} -> Normalized: {normalize_field_name(case)}")
