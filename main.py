import json
import os
from pdf_extractor import extract_pdf_text
from agents import call_extractor, call_critic_master
from models import ExtractorOutput

def main_loop(pdf_path: str, ground_truth_text: str):
    pdf_text = extract_pdf_text(pdf_path)
    final_output = None
    score = 0
    loop_count = 0

    while loop_count < 3 and score < 8:
        print(f"🔄 第 {loop_count+1} 轮提取...")
        is_few_shot = (loop_count > 0)
        few_shot_context = ""
        if is_few_shot and os.path.exists("evolution.jsonl"):
            with open("evolution.jsonl", "r", encoding="utf-8") as f:
                few_shot_context = f.read()
                
        extractor_res = call_extractor(pdf_text, is_few_shot, few_shot_context)
        
        if extractor_res.abstain:
            print("⚠️ Extractor 触发 Abstain：数据缺失，不再强行硬算！")
            final_output = extractor_res
            break

        critic_res = call_critic_master(extractor_res.model_dump(), ground_truth_text)
        critic_data = json.loads(critic_res)
        score = critic_data.get("score", 0)
        feedback = critic_data.get("feedback", "无具体反馈")
        print(f"🔍 CriticMaster 评分：{score}，反馈：{feedback}")

        if score >= 8:
            final_output = extractor_res
            print("✅ 分数达标，直接通过！")
            break
        else:
            print("❌ 分数不达标，准备下一轮修正...")
            log = {
                "loop": loop_count,
                "score": score,
                "feedback": feedback,
                "extracted_data": extractor_res.model_dump()
            }
            with open("evolution.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(log, ensure_ascii=False) + "\n")
                
        loop_count += 1

    if score < 8 and not extractor_res.abstain:
        print("🛑 超轮次未达标，系统启动 Abstain 兜底，强制转入人工审核。")
        final_output = ExtractorOutput(
            company=extractor_res.company,
            resources=[],
            abstain=True,
            reasoning="经过 3 轮修正，CriticMaster 判定准确性依然不达标。"
        )

    print("\n📊 最终输出结果：")
    print(final_output.model_dump_json(indent=2))

if __name__ == "__main__":
    main_loop("mock.pdf", "Indicated: 500Mt @ 1.2g/t")