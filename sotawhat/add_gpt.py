import os
from openai import OpenAI
import requests
import time
import json
import time

API_SECRET_KEY = "sk-zk2430a6a5d06128d132e17dc544fcf747a67d2cb95a2d05";
BASE_URL = "https://api.zhizengzeng.com/v1/"

# chat with other model
def chat_completions(query):
    client = OpenAI(api_key=API_SECRET_KEY, base_url=BASE_URL)
    resp = client.chat.completions.create(
        model="ERNIE-Speed-8K",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": query}
        ]
    )
    print(resp)
    print(resp.choices[0].message.content)
    
if __name__ == '__main__':
    chat_completions("Now I will provide a title and an abstract of a paper. Please read them carefully and answer the following questions:\n"+
    "Is it focusing on the topic of large reasoning model safety? only answer with a word (true or false) and a number ranging from 0-5 indicating the intense of relation. 5 means the whole paper is about the Large reasoning model safety, while 0 means it is absolutely unrelated.\n"+
    "Neuromorphic Principles for Efficient Large Language Models on Intel Loihi 2 (['Steven Abreu', 'Sumit Bam Shrestha', 'Rui-Jie Zhu', 'Jason Eshraghian'] - 11 February, 2025)\
Large language models (LLMs) deliver impressive performance but require large amounts of energy. In this work, we present a MatMul-free LLM architecture adapted for Intel's neuromorphic processor, Loihi 2. Our approach leverages Loihi 2's support for low-precision, event-driven computation and stateful processing. Our hardware-aware quantized model on GPU demonstrates that a 370M parameter MatMul-free model can be quantized with no accuracy loss. Based on preliminary results, we report up to 3x higher throughput with 2x less energy, compared to transformer-based LLMs on an edge GPU, with significantly better scaling. Further hardware optimizations will increase throughput and decrease energy consumption. These results show the potential of neuromorphic hardware for efficient inference and pave the way for efficient reasoning models capable of generating complex, long-form text rapidly and cost-effectively.\
Link: https://arxiv.org/abs/2503.18002"
    )