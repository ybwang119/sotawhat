import os
from openai import OpenAI
from openai import APITimeoutError
import requests
import time
import json
import time
import re
API_SECRET_KEY = "sk-zk2430a6a5d06128d132e17dc544fcf747a67d2cb95a2d05";
BASE_URL = "https://api.zhizengzeng.com/v1/"

# chat with other model
class gpt_marker:
    def __init__(self, api_key=API_SECRET_KEY, model="glm-4-flash",base_url=BASE_URL):
        self.api_key = api_key
        self.model = model
        self.messages = [{"role": "system", "content": "You are a paper reader to filer papers related to the large language model with **reasoning capability**. \
                          reasoning capability is a capability of the newest large language model, **which could generate thinking process before generating answers**.\
                          Keep in mind to **distinguish large language model with reasoning capability from normal large language model**!"}]
        self.base_url=base_url
        self.client=OpenAI(api_key=API_SECRET_KEY, base_url=BASE_URL)
        # self.query=[
        #     "Now I will provide a title and an abstract of a paper. Please read them carefully and answer the question.\n"+
        #     "Paper info:\n"+"{}"+
        #     "Question:\n"+
        #     "Does it mention any topics related to 'large reasoning models safety'(include but not limited to any attacks and defenses), for example, deepseek-r1 or gpt-o1 (both of which are reasoning models based on chain-of-thought (CoT) techniques)? Keep in mind to **distinguish large reasoning model from large language model**! Simply related to LLM safety can not be counted as a positive one. Also, the paper does not have to only focus on LRM.\n"+
        #     "Answer format:\n"+
        #     "First show your thinking contents and then conclude with a word (true or false) and a number ranging from 0-10 indicating the intense of relation.\
        #     10 means the whole paper is totally about the mentioned topic, while 0 means it is absolutely unrelated. If the first answer is false, then the score should be 0.\n"+
        #     "Example format: '**Conclusion: True, 6**'\n"+
        #     "Do not add more contents after showing the score.\n\n"+
        #     "Now start your analysis:\n",
        #     "What is the aim of the paper? Does it propose a new way to attack the model, or propose a new defense method to protect the model,\
        #     or a study to get some conclusions, or a benchmark assessing the capability of the models, or a survey covering the development of the field?"+
        #     "Answer format:\n"+
        #     "First show your thinking contents and then conclude with a word (attack, defense, study, benchmark or survey).\n"+
        #     "Example format: '**Conclusion: study**'\n"+
        #     "Do not add more contents after showing the conclusion.\n\n"+
        #     "Now start your analysis:\n",
        # ]
        self.query=[
            "Now I will provide a title and an abstract of a paper. Please read them carefully and analyze the questions.\n"+
            "Paper info:\n"+"{}"+
            "Question:\n"+
            "Does it mention any topics related to large language models?\n"+
            "Does it mention any topics related to models safety(include but not limited to any attacks and defenses)?\n"+
            "Does it mention any topics related to llm with reasoning capability or chain-of-thought capability (such as gpt-o1, qwq, deepseek-r1 or kimi-1.5-think)?\n"+
            "Answer format:\n"+
            "First show your reasoning contents and then conclude with a word (true or false) and a number ranging from 0-10 indicating the intense of relation.\
            10 means the whole paper is totally about the mentioned topic and has positive answers for ALL questions,\
            while 0 means it is absolutely unrelated to any questions above. If the first answer is false, then the score should be low.\
            **Only all papers with all positive answers could have a score higher than 6.**\n"+
            "After analyzing all questions, you could provide ONE conclusion for the paper. Example format: '**Conclusion: True, 6**'\n"+
            "Do not add more contents after showing the score. Do not attach every question with a conclusion, either.\n\n"+
            "Now start your analysis:\n",
            "What is the aim of the paper? Does it propose a new way to attack the model, or propose a new defense method to protect the model,\
            or a study to get some conclusions, or a benchmark assessing the capability of the models, or a survey covering the development of the field?"+
            "Answer format:\n"+
            "First show your thinking contents and then conclude with a word (attack, defense, study, benchmark or survey).\n"+
            "Example format: '**Conclusion: study**'\n"+
            "Do not add more contents after showing the conclusion.\n\n"+
            "Now start your analysis:\n",
        ]
        # self.query=[
        #     "Now I will provide a title and an abstract of a paper. Please read them carefully and analyze the questions.\n"+
        #     "Paper info:\n"+"{}"+
        #     "Question:\n"+
        #     "Does it mention any topics related to large language models?\n"+
        #     "Does it mention any topics related to models safety(include but not limited to any attacks and defenses)?\n"+
        #     "Does it mention any topics related to llm with reasoning capability or chain-of-thought capability (such as gpt-o1, qwq, deepseek-r1 or kimi-1.5-think)?\n"+
        #     "Answer format:\n"+
        #     "First show your reasoning contents and then **sum up the number of positive answers**. \
        #     3 means the whole paper is totally about the mentioned topic and has positive answers for ALL three questions,\
        #     while 0 means it is absolutely unrelated to any questions above.\
        #     **Only all papers with all positive answers could have a score of 3.** Similarly, 2 for 2 positive answers and 1 for 1 positive answer.\n"+
        #     "After analyzing all questions, you could provide ONE number for the paper. Example format: '**Conclusion: 2**'\n"+
        #     "Do not add more contents after showing the score.\n\n"+
        #     "Now start your analysis:\n",
        #     "What is the aim of the paper? Does it propose a new way to attack the model, or propose a new defense method to protect the model,\
        #     or a study to get some conclusions, or a benchmark assessing the capability of the models, or a survey covering the development of the field?"+
        #     "Answer format:\n"+
        #     "First show your thinking contents and then conclude with a word (attack, defense, study, benchmark or survey).\n"+
        #     "Example format: '**Conclusion: study**'\n"+
        #     "Do not add more contents after showing the conclusion.\n\n"+
        #     "Now start your analysis:\n",
        # ]
        self.related=False
        self.related_score=0
        self.classification=False
        self.reason=None
    def get_chat_completion_with_retry(self, max_retries=None, initial_delay=5, backoff_factor=2):
        retry_count = 0
        current_delay = initial_delay
        
        while True:
            try:
                raw_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    temperature=0.,
                )
                return raw_response
            except APITimeoutError as e:
                retry_count += 1
                if max_retries is not None and retry_count > max_retries:
                    raise Exception(f"API请求超时，已达到最大重试次数 {max_retries}") from e
                
                print(f"API请求超时，等待{current_delay}秒后重试... (尝试次数: {retry_count})")
                time.sleep(current_delay)
                current_delay *= backoff_factor  # 指数退避
            except Exception as e:
                raise e
    def analyze(self,paper):
        self.messages.append({"role": "user", "content": self.query[0].format(paper)})
        raw_response=self.get_chat_completion_with_retry()
        response=raw_response.choices[0].message.content

        self.reason=response
        self.related="True" in response.split("Conclusion:")[-1]
        self.related_score=int(re.findall(r"\d+",response.split("Conclusion:")[-1])[0])

        if self.related and self.related_score>5:
            self.messages.append({"role": "assistant", "content": response})
            self.messages.append({"role": "user", "content": self.query[1].format()})
            raw_response=self.get_chat_completion_with_retry()
            response=raw_response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": response})
            self.classification=response.split("**Conclusion: ")[-1][:-2]
            # print(response.split("**Conclusion: ")[-1][:-2])
            return 0
    
if __name__ == '__main__':
    paper="sudo rm -rf agentic_security (Sejin Lee - 26 March, 2025) \
Large Language Models (LLMs) are increasingly deployed as computer-use agents, autonomously performing tasks within real desktop or web environments. While this evolution greatly expands practical use cases for humans, it also creates serious security exposures. We present SUDO (Screen-based Universal Detox2Tox Offense), a novel attack framework that systematically bypasses refusal trained safeguards in commercial computer-use agents, such as Claude Computer Use. The core mechanism, Detox2Tox, transforms harmful requests (that agents initially reject) into seemingly benign requests via detoxification, secures detailed instructions from advanced vision language models (VLMs), and then reintroduces malicious content via toxification just before execution. Unlike conventional jailbreaks, SUDO iteratively refines its attacks based on a built-in refusal feedback, making it increasingly effective against robust policy filters. In extensive tests spanning 50 real-world tasks and multiple state-of-the-art VLMs, SUDO achieves a stark attack success rate of 24% (with no refinement), and up to 41% (by its iterative refinement) in Claude Computer Use. By revealing these vulnerabilities and demonstrating the ease with which they can be exploited in real-world computing environments, this paper highlights an immediate need for robust, context-aware safeguards. WARNING: This paper includes harmful or offensive model outputs.\
Link: https://arxiv.org/abs/2503.20279"
    paper_reader=gpt_marker()
    paper_reader.analyze(paper)