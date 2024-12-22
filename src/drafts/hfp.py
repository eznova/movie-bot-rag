from langchain_huggingface import HuggingFaceLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from huggingface_hub import InferenceClient
import os

# Токен из .env файла
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Инициализация клиента InferenceClient
client = InferenceClient(
    model="gpt-3.5-turbo",  # Модель GPT-3.5
    token=HUGGINGFACE_API_TOKEN
)

# Использование HuggingFaceLLM для интеграции с моделью
huggingface_llm = HuggingFaceLLM(client=client)

# Создание шаблона запроса (PromptTemplate)
prompt_template = PromptTemplate(
    template="Какие фильмы о путешествиях ты знаешь?",
    input_variables=["query"]
)

# Создание LLMChain с HuggingFaceLLM
llm_chain = LLMChain(llm=huggingface_llm, prompt=prompt_template)

# Запуск цепочки с примером запроса
response = llm_chain.run(query="films about travel")
print(response)
