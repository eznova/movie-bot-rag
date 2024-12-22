import ollama, chardet, docx, chromadb
from tkinter.filedialog import askopenfilename as ask
from nltk import sent_tokenize as st

#В общем, суть такова. По запросу пользователя генерируем набор из 5 запросов машины "по мотивам."
#Эти "по мотивам" прогоняем через эмбед-поиск.
#Результаты суём в ответ на изначальный вопрос.
#Profit!
#Ещё идея в том, чтобы пересказывать куски текста.

client = chromadb.Client()
collection = client.create_collection(name="docs")

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

def create_db():
    global collection
    file = ask()
    text = new_gettext(file)
    sents = st(text)

    for i,d in enumerate(sents):
        #response = ollama.embeddings(model="nomic-embed-text", prompt=d) #Попробовать другой эмбеддер?
        #response = ollama.embeddings(model="mxbai-embed-large", prompt=d)
        response = ollama.embeddings(model="snowflake-arctic-embed", prompt=d)
        embedding = response["embedding"]
        collection.add(
        ids=[str(i)],
        embeddings=[embedding],
        documents=[d])

def query():
    global collection
    userprompt = input('Введите вопрос:\n')
    reprompt = ollama.generate(
    model = "llama3.1:8b",
    prompt=f"{userprompt}. Переформулируй этот вопрос пятью способами, будь точным, избегай новых деталей; каждое предложение закончи символом #."
    )
    prompts = reprompt['response'].split('#') + [f'{userprompt}'] 
    prompts = [p for p in prompts if len(p)>1]
    print(prompts)
    response = []
    for i in prompts:
        question = ollama.embeddings(
        prompt=i,
        #model="nomic-embed-text"
        #model='mxbai-embed-large'
        model = 'snowflake-arctic-embed'
        )
        results = collection.query(
        query_embeddings=[question["embedding"]],
        n_results=5 #Может, больше результатов брать?
        )
        [response.append(n) for i in results['documents'] for n in i]
    #print('Результаты')
    #print(results)
    #data = results['documents'][0][0]
    #print(data)
    data = ' '.join(response)
    #print(data)
    output = ollama.generate(
    #model="gemma:2b",
    model = "llama3.1:8b",
    prompt=f"Using this data: {data}. Respond to this prompt: {userprompt}"
    )
    print(output['response'])

def simple_query():
    file = ask(title='Выберите текст.')
    text = new_gettext(file)
    userprompt = input()
    output = ollama.generate(
    #model="gemma:2b",
    model = "llama3.1:8b",
    prompt=f"Using this data: {text}. Respond to this prompt: {userprompt}"
    )
    print(output)


def main():
    continuation = '5'
    while continuation != '4':
        print(continuation)
        if continuation == '1':
            print('Вы выбрали создание базы данных!')
            create_db()
        elif continuation == '2':
            print('Вы выбрали диалог.')
            query()
        elif continuation == '3':
            print('Вы выбрали запрос по тексту из контекстного окна.')
            simple_query()
        elif continuation == '4':
            print('Всего доброго!')
        continuation = input('(1) Создать базу данных. (2) Запросить. (3) Запрос по тексту без создания базы. (4) Выйти.')

main()