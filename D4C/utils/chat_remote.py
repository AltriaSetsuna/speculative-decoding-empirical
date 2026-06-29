import asyncio
import os
import requests
import time
from retry import retry

class RemoteChat:
    def __init__(self, api_key, model, proxy):
        self.api_key = api_key
        self.model = model
        self.proxy = proxy

    @retry(tries=3, delay=2, backoff=2)
    def safe_request(self, url, data, headers):
        response = requests.post(url, json=data, headers=headers)
        # print(response.json())
        # exit()
        return response.json()
        
    def chat(self, prompt, ID, temperature=0.0):
        data = {
            'model': self.model,
            'messages': prompt,
            'temperature': temperature,
            'chat_template_kwargs': {'enable_thinking': False},
        }
        if self.proxy == 'AI':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            url = 'https://api.ai-gaochao.cn/v1/chat/completions'
        elif self.proxy == 'OMG':
            headers = {
                'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            url = 'https://aigptx.top/v1/chat/completions'
        elif self.proxy == 'OpenAI':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            url = 'https://api.openai.com/v1/chat/completions'
        else:
            raise ValueError("proxy must be 'AI', 'OMG', or 'OpenAI'")
        ti = 0
        while ti <= 10:
            response_api = self.safe_request(url, data, headers)
            try:
                response = response_api['choices'][0]['message']['content']
                print(f"ID: {ID}:\tSuccessfully made request")
                break
            except Exception as e:
                print(f"ID: {ID}:\t{response_api}")
                response = None
                ti += 1
                time.sleep(3)
        return response


class AsyncRemoteChat:
    def __init__(self, api_key, model, proxy, batch_size=8):
        self.api_key = api_key
        self.model = model
        self.proxy = proxy
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(batch_size)

    def endpoint(self):
        if self.proxy == 'AI':
            return 'https://api.ai-gaochao.cn/v1/chat/completions'
        if self.proxy == 'OMG':
            return 'https://aigptx.top/v1/chat/completions'
        if self.proxy == 'OpenAI':
            return 'https://api.openai.com/v1/chat/completions'
        if self.proxy == 'OpenAICompatible':
            base_url = os.environ.get('OPENAI_API_BASE') or os.environ.get('OPENAI_BASE_URL')
            if not base_url:
                raise ValueError('OPENAI_API_BASE or OPENAI_BASE_URL is required for OpenAICompatible')
            return base_url.rstrip('/') + '/chat/completions'
        raise ValueError("proxy must be 'AI', 'OMG', 'OpenAI', or 'OpenAICompatible'")

    async def chat(self, prompt, ID, temperature=0.0):
        data = {
            'model': self.model,
            'messages': prompt,
            'temperature': temperature,
            'chat_template_kwargs': {'enable_thinking': False},
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }
        url = self.endpoint()
        async with self.semaphore:
            response = None
            for attempt in range(11):
                try:
                    def do_request():
                        response = requests.post(url, json=data, headers=headers, timeout=600)
                        if response.status_code == 404:
                            raise RuntimeError(response.text)
                        response.raise_for_status()
                        return response.json()

                    response_api = await asyncio.to_thread(do_request)
                    response = response_api['choices'][0]['message']['content']
                    print(f"ID: {ID}:\tSuccessfully made request")
                    return response
                except Exception as e:
                    print(f"ID: {ID}:\t{e}")
                    response = None
                    if "404" in str(e) or "does not exist" in str(e):
                        break
                    if attempt < 10:
                        await asyncio.sleep(3)
            return response
