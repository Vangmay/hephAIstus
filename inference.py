import os
from cerebras.cloud.sdk import Cerebras
import dotenv

dotenv.load_dotenv()

client = Cerebras(
    # This is the default and can be omitted
    api_key=os.environ.get("cerebras_api_key"),
)

stream = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "Hello you an assistant"
        }
    ],
    model="qwen-3-coder-480b",
    stream=True,
    max_completion_tokens=40000,
    temperature=0.57,
    top_p=0.8
)

for chunk in stream:
  print(chunk.choices[0].delta.content or "", end="")
print("\n")