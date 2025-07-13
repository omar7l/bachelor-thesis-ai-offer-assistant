# vector_store_utils.py

import os
import json
from sentence_transformers import SentenceTransformer
import chromadb

# --- CONSTANTS ---
VECTOR_STORE_PATH = "vector_store"
COLLECTION_NAME = "offer_positions"
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'

# --- INITIALIZE CLIENTS ---
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
chroma_client = chromadb.PersistentClient(path=VECTOR_STORE_PATH)
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

# --- VECTOR STORE FUNCTIONS ---
def load_and_vectorize_offers(data_dir: str):
    print(f"Checking collection '{COLLECTION_NAME}' for existing documents...")
    if collection.count() > 0:
        print(f"Collection already contains {collection.count()} documents. Skipping vectorization.")
        print("If you want to re-vectorize, please clear the 'vector_store' directory and run again.")
        return

    print(f"Vectorizing offers from directory: {data_dir}")
    texts_to_embed = []
    metadatas = []
    ids = []

    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    offer_data = json.load(f)
                offer_id = offer_data.get("offer_id", "unknown_offer")
                for pos_idx, position in enumerate(offer_data.get("positions", [])):
                    description = position.get("description")
                    title = position.get("position_title", f"Position {pos_idx+1}")
                    if description:
                        text_content = f"Offer Position Title: {title}\nDescription: {description}"
                        texts_to_embed.append(text_content)
                        metadatas.append({
                            "offer_id": offer_id,
                            "position_id": position.get("position_id", str(pos_idx+1)),
                            "position_title": title,
                            "source_file": filename
                        })
                        ids.append(f"{offer_id}_{position.get('position_id', str(pos_idx+1))}")
            except Exception as e:
                print(f"Warning: Error processing {filename}: {e}")

    if texts_to_embed:
        print(f"Generating embeddings for {len(texts_to_embed)} position descriptions...")
        embeddings = embedding_model.encode(texts_to_embed, show_progress_bar=True).tolist()
        print(f"Adding {len(texts_to_embed)} items to ChromaDB collection '{COLLECTION_NAME}'...")
        collection.add(embeddings=embeddings, documents=texts_to_embed, metadatas=metadatas, ids=ids)
        print(f"Successfully added {collection.count()} documents to the collection.")
    else:
        print("No offer descriptions found to vectorize.")

def retrieve_context(query_text, n_results=3):
    print(f"\nRetrieving context for RAG based on query: '{query_text[:100]}...'")
    query_embedding = embedding_model.encode(query_text).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=['documents', 'metadatas']
    )
    retrieved_docs = []
    if results and results.get('documents') and results['documents'][0]:
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i] if results.get('metadatas') and results['metadatas'][0] else {}
            retrieved_docs.append({
                "content": doc,
                "offer_id": metadata.get("offer_id"),
                "position_id": metadata.get("position_id"),
                "position_title": metadata.get("position_title"),
            })
        print(f"Retrieved {len(retrieved_docs)} relevant contexts for RAG.")
    else:
        print("No relevant contexts found for RAG.")
    return retrieved_docs
