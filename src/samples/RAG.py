from langchain_openai import ChatOpenAI
from langchain import hub
from langchain_chroma import Chroma
from langchain.schema.document import Document
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import CharacterTextSplitter
from tkinter.filedialog import askopenfilename as ask
import chardet, docx

def new_gettext(file):
    try:
        if file.endswith('.txt'):
            text = open(rf'{file}','rb')
            text_body = text.read()
            enc = chardet.detect(text_body).get("encoding")
            if enc and enc.lower() != "utf-8" and enc.lower() != "windows-1251":
                text_body = text_body.decode(enc)
                text_body = text_body.encode("utf-8")
                text_body = text_body.decode("utf-8")
                return text_body
            elif enc and enc.lower() == "windows-1251":
                text = open(rf'{file}', 'r', encoding = 'windows-1251')
                text_body = text.read()
                text.close()
                return text_body
            else:
                text = open(rf'{file}', 'r', encoding = 'UTF-8')
                text_body = text.read()
                text.close()
                return text_body
        elif file.endswith('.docx'):
            doc = docx.Document(rf'{file}')
            text = (paragraph.text for paragraph in doc.paragraphs)
            text_body = '\n'.join(text)
            return text_body
        else:
            pass
    except:
        pass


#Это рабочий вариант чат-бота с контекстом.

chat = ChatOpenAI(model="gpt-4o-mini", base_url=r"ЗДЕСЬ_ПРОКСИ", api_key="СВОЙ_КЛЮЧ")
embedder = OpenAIEmbeddings(base_url=r"ЗДЕСЬ_ПРОКСИ", api_key="СВОЙ_КЛЮЧ")

def text_chunks(text): #Функция, разбивающая документы на куски
    splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
    documents = [Document(page_content=x) for x in splitter.split_text(text)]
    return documents

file = ask()
text = new_gettext(file)
docs = text_chunks(text)
#print(docs[0:2])

vectorstore = Chroma.from_documents(documents=docs, embedding=embedder)

retriever = vectorstore.as_retriever()
prompt = hub.pull("rlm/rag-prompt") #Из базы промптов выбираем промпт, нацеленный на поиск по контексту

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | chat
    | StrOutputParser()
)

query = input('Задайте свой вопрос:\n')
answer = rag_chain.invoke(query)

print(answer)