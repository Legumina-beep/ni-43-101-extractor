import os
import json
import re
from langchain_openai import ChatOpenAI
from models import ExtractorOutput

# ================= 配置区 =================
LLM_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY", "sk-ebfa55dca4da466195e1aab7c80cedaa"),
    "base_url": os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
}

# ================= 核心清洗算法 =================
def extract_json_from_llm(raw_text: str) -> str:
    if not raw_text:
        return "{}"
    match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
    if match:
        return match.group(1)
    return "{}"

def call_extractor(pdf_text: str, is_few_shot: bool = False, few_shot_text: str = ""):
    llm = ChatOpenAI(
        openai_api_key=LLM_CONFIG["api_key"],
        openai_api_base=LLM_CONFIG["base_url"],
        model="deepseek-chat",
        temperature=0.1
    )
    
    # =============== 核心修正：给出极其严格的 JSON 结构模板 ===============
    sys_prompt = """
    你是一个资深采矿工程师，专精于 NI 43-101 报告的数据提取。
    【任务】：从给定的表格文本中，提取 Indicated 和 Inferred 资源量。
    
    【核心硬性约束（绝对不能违背）】：
    1. 绝对不要输出任何 Markdown 标记（比如 ```json 或 ```），直接输出纯 JSON 字符串。
    2. 不要添加任何解释性文字！
    3. 必须严格遵循以下 JSON 格式返回（数据可以填你提取到的，但字段名字和结构一个都不能变）：
    {
        "company": "公司名称字符串",
        "resources": [
            {
                "resource_type": "Indicated",
                "ore_mt": 150.0,
                "grade_au_gt": 1.2,
                "metal_oz": 5800000
            },
            {
                "resource_type": "Inferred",
                "ore_mt": 50.0,
                "grade_au_gt": 1.0,
                "metal_oz": 1600000
            }
        ],
        "abstain": false,
        "reasoning": "如果 abstain 为 true，请在这里写弃权的原因；否则给个空字符串"
    }
    4. 如果表格中根本没有相应的矿石量或品位数据，绝对不要瞎编，`abstain` 必须设为 true，并且把 `resources` 数组置空。
    """
    # =====================================================================

    if is_few_shot and few_shot_text:
        sys_prompt += f"\n【纠错参考】：以下是之前提取时犯过的错误案例，请警惕：\n{few_shot_text}"
    
    user_prompt = f"表格数据：\n{pdf_text}"
    response = llm.invoke(f"{sys_prompt}\n\n{user_prompt}")

    cleaned_json = extract_json_from_llm(response.content)
    return ExtractorOutput.model_validate_json(cleaned_json)

def call_critic_master(extracted_json: dict, ground_truth_text: str):
    llm = ChatOpenAI(
        openai_api_key=LLM_CONFIG["api_key"],
        openai_api_base=LLM_CONFIG["base_url"],
        model="deepseek-chat",
        temperature=0.0
    )
    sys_prompt = """
    你是一个铁面无私的 NI 43-101 报告质检员。
    给提取结果打分（1-10分）。
    评分逻辑：准确率在 ±5% 内得 8-10 分；有明显错误得 5-7 分；强行瞎编得 0-4 分。
    输出必须是纯 JSON 格式：{"score": 8, "feedback": "具体修正意见"}
    """
    user_prompt = f"Ground Truth 真实数据：{ground_truth_text}\nAI 当前提取结果：{extracted_json}"
    response = llm.invoke(f"{sys_prompt}\n\n{user_prompt}")
    return response.content