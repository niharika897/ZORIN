import asyncio
from memory.memory_manager import MemoryManager
from memory.memory_extractor import MemoryExtractor

text = """
User: I am building a personal AI assistant called ZORIN.
I want to become an AI engineer.
I prefer highly animated interfaces rather than minimalistic designs.
"""

extractor = MemoryExtractor(MemoryManager())

result = asyncio.run(extractor.extract(text))

print("\nEXTRACTED MEMORIES:")
print(result)