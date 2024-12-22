import chromadb

def test_chromadb_connection():
    try:
        # Используем только Client() для локального подключения
        client = chromadb.Client()
        collection = client.create_collection(name="test")
        print("Connection successful!")
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")

test_chromadb_connection()
