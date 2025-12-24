from neo_rag_prompts import QA_PROMPT, SUMM_PROMPT, COMPARE_PROMPT

# 例：問 AXI 帶寬配置
prompt = QA_PROMPT.format(
    question="Neo210 的 AXI subordinate 512-bit 要達成 16GB/s 的時脈與效率條件？",
    context="\n\n".join(topk_texts)  # 檢索到的片段
)
