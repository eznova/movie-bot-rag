import logging
import chromadb
import nltk
from nltk import sent_tokenize as st
import requests
import io
import os
from telebot import TeleBot
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer  # Импортируем для локальных эмбеддингов
import spacy  # Для извлечения сущностей из текста

# Загрузка переменных окружения из .env файла
load_dotenv()

nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание клиента ChromaDB и коллекции на уровне модуля
client = chromadb.Client()

# Создаем коллекцию без указания embedding_dim
collection = client.create_collection(name="docs")

# Инициализация модели для получения эмбеддингов
model = SentenceTransformer('all-MiniLM-L6-v2')  # Используем локальную модель для эмбеддингов

# Загрузка модели spaCy для распознавания сущностей
nlp = spacy.load("en_core_web_sm")

# Функция для проверки работоспособности клиента и коллекции
# def check_chromadb_connection(client, collection):
#     try:
#         if client is not None and collection is not None:
#             logger.info("ChromaDB client and collection are available.")
#             test_data = "test_document"
#             collection.add(
#                 ids=["test_id"],
#                 embeddings=[[0.0]*384],  # Пустой эмбеддинг размером 384 для теста
#                 documents=[test_data]
#             )
#             retrieved = collection.get([str("test_id")])
#             if retrieved:
#                 logger.info("Successfully retrieved test data from ChromaDB.")
#                 return True
#             else:
#                 logger.error("Test data retrieval failed.")
#                 return False
#         else:
#             logger.error("ChromaDB client or collection is not initialized.")
#             return False
#     except Exception as e:
#         logger.error(f"Error checking ChromaDB connection: {e}")
#         return False

# # Проверка соединения с ChromaDB после инициализации
# if not check_chromadb_connection(client, collection):
#     logger.error("ChromaDB client is not working properly.")
# else:
#     logger.info("ChromaDB client is connected and ready for use.")

# Функция для получения текста из файла
def new_gettext(file_content, file_name):
    try:
        if file_name.endswith('.txt'):
            text = file_content.decode("utf-8")
            logger.info(f"Extracted text from {file_name}.")
            return text
        elif file_name.endswith('.docx'):
            import docx
            doc = docx.Document(io.BytesIO(file_content))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            logger.info(f"Extracted text from {file_name}.")
            return text
        else:
            logger.warning(f"Unsupported file format: {file_name}")
            return None
    except Exception as e:
        logger.error(f"Error processing file {file_name}: {e}")
        return None

# Функция для создания базы данных в ChromaDB
def create_db(file_content, file_name):
    global collection
    text = new_gettext(file_content, file_name)
    if not text:
        return "Ошибка при обработке файла."
    
    sents = st(text)  # Токенизация текста на предложения
    logger.info(f"Tokenized {len(sents)} sentences from the text.")

    # # Проверяем соединение с ChromaDB перед добавлением данных
    # if not check_chromadb_connection(client, collection):
    #     return "Ошибка: ChromaDB недоступен."

    for i, d in enumerate(sents):
        try:
            # Генерация эмбеддинга для предложения
            logger.info(f"Generating embedding for sentence {i}.")
            embedding = model.encode(d)  # Используем SentenceTransformer для генерации эмбеддингов
            logger.info(f"Adding sentence {i} with embedding: {embedding[:10]}...")

            # Добавляем эмбеддинг в коллекцию
            try:
                collection.add(
                    ids=[str(i)],
                    embeddings=[embedding],
                    documents=[d]
                )
                logger.info(f"Successfully added sentence {i} to ChromaDB.")
            except Exception as e:
                logger.error(f"Error adding sentence {i} to ChromaDB: {e}")
                return f"Ошибка при добавлении предложения {i} в базу данных."

        except Exception as e:
            logger.error(f"Error during embedding or adding sentence {i} to ChromaDB: {e}")
            return "Ошибка при генерации эмбеддинга или добавлении данных в базу."

    return "База данных успешно создана!"

# Функция для обработки загрузки файла через Telegram API
def process_file(file_id, bot, file_name):
    try:
        # Получаем файл из Telegram по file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
        response = requests.get(file_url)
        
        # Если ответ успешен, передаем содержимое в create_db
        if response.status_code == 200:
            file_content = response.content
            logger.info(f"File {file_name} downloaded successfully.")
            return create_db(file_content, file_name)
        else:
            logger.error(f"Failed to download file from Telegram: {response.status_code}")
            return "Ошибка при скачивании файла."
    except Exception as e:
        logger.error(f"Error processing file {file_id}: {e}")
        return "Ошибка при обработке файла."

# Функция для извлечения сущностей из текста с использованием spaCy
def extract_entities(text):
    """
    Использует spaCy для извлечения сущностей (имена, даты, локации и т.д.)
    """
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        entities.append((ent.text, ent.label_))
    return entities

# Функция для поиска по базе данных ChromaDB
def search_in_db(query, collection, top_k=5):
    try:
        # Генерация эмбеддинга для запроса
        query_embedding = model.encode(query)
        logger.info(f"Generated embedding for query: {query[:30]}...")

        # Поиск схожих предложений в базе данных
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        if not results['documents']:
            return "Извините, я не нашел подходящих документов."

        # Формируем отформатированный ответ с наиболее релевантными результатами
        response = "Вот что я нашел по вашему запросу:\n"
        for i, doc in enumerate(results['documents']):
            # Преобразуем список в отформатированный текст
            formatted_doc = "\n".join(doc)  # Это позволяет выводить строки в более удобном виде
            response += f"{i+1}:\n{formatted_doc}\n\n"  # Добавляем пробелы между результатами

        return response

    except Exception as e:
        logger.error(f"Error during search in ChromaDB: {e}")
        return "Произошла ошибка при поиске."




# Хендлер для команды /start
def start(message, bot):
    try:
        user_id = message.chat.id
        logger.info(f"User {user_id} triggered /start command.")
        welcome_message = "Привет! 👋\n"
        welcome_message += "Я бот, который поможет вам найти фильмы по описаниям! 🎥\n"
        welcome_message += "Загрузите .txt или .docx файл с описаниями фильмов, и я помогу вам найти информацию по запросу! 🍿"
        bot.send_message(user_id, welcome_message)
    except Exception as e:
        logger.error(f"Error processing /start command: {e}")

# Обработка файлов, загруженных пользователями
def handle_document(message, bot):
    try:
        # Проверяем, что файл имеет правильный формат
        file_name = message.document.file_name
        if file_name.endswith('.txt') or file_name.endswith('.docx'):
            file_id = message.document.file_id
            logger.info(f"User {message.chat.id} uploaded a file {file_name}.")
            result = process_file(file_id, bot, file_name)
            bot.send_message(message.chat.id, result)
        else:
            bot.send_message(message.chat.id, "Пожалуйста, загрузите файл с расширением .txt или .docx.")
    except Exception as e:
        logger.error(f"Error handling file upload: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при загрузке файла.")

# Основной код бота
load_dotenv()  # Загружаем переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Получаем токен из переменной окружения
bot = TeleBot(BOT_TOKEN)  # Создаем объект бота

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_description_query = message.text

    # Приветственное сообщение
    if "/start" in user_description_query:
        welcome_message = "Привет! 👋\n"
        welcome_message += "Я бот, который поможет вам найти фильмы по описаниям! 🎥\n"
        welcome_message += "Загрузите .txt файл с описаниями фильмов или попробуйте сразу задать вопрос о фильме, и я помогу вам найти информацию по запросу! 🍿"
        bot.send_message(user_id, welcome_message)
        logger.info(f"User {user_id} triggered /start command.")

# Хендлер для обработки текстовых запросов
@bot.message_handler(func=lambda message: True)
def handle_query(message):
    try:
        user_id = message.chat.id
        user_query = message.text  # Текст запроса пользователя
        logger.info(f"User {user_id} asked: {user_query}")

        # Поиск по базе данных
        result = search_in_db(user_query, collection)

        # Отправка результата пользователю
        bot.send_message(user_id, result)
    except Exception as e:
        logger.error(f"Error handling query: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при обработке вашего запроса.")

# Регистрация хендлеров
@bot.message_handler(commands=['start'])
def handle_start(message):
    start(message, bot)

@bot.message_handler(content_types=['document'])
def handle_uploaded_document(message):
    handle_document(message, bot)

# Запуск бота
if __name__ == "__main__":
    try:
        logger.info("Bot started")
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
