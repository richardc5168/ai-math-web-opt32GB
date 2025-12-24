from neo_rag_prompts import PPA_ANALYSIS_PROMPT
from rag_backend import Retriever

r = Retriever("knowledge.db")
hits = r.search("Neo210 AXI DMA power efficiency")
ctx = "\n".join([h['text'] for h in hits])

prompt = PPA_ANALYSIS_PROMPT.format(question="Neo210 DMA 的功耗影響", context=ctx)
print(prompt)
