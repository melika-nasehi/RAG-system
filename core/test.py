from generation.rag_chain import RagChain

chain = RagChain()
answer = chain.ask("حداکثر تعداد واحد درسی در هر نیمسال چند است؟")

print(answer.text)
print("\nsources:")
for source in answer.sources():
    print(f"  {source}")