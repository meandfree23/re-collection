import os
import json
import time
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import chromadb
from chromadb.utils import embedding_functions

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
collection = chroma_client.get_or_create_collection(name="bookmarks", embedding_function=sentence_transformer_ef)

def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    start = 0
    text_len = len(text)
    if text_len == 0:
        return chunks
    while start < text_len:
        chunks.append(text[start:start + chunk_size])
        start += chunk_size - overlap
    return chunks

def fetch_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = soup.title.string if soup.title else ""
        
        # Extract image (og:image or first img tag)
        image_url = ""
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            image_url = og_image["content"]
        else:
            img_tag = soup.find("img")
            if img_tag and img_tag.get("src"):
                image_url = img_tag["src"]
                # Convert relative to absolute if necessary (simple heuristic)
                if image_url.startswith('/'):
                    from urllib.parse import urljoin
                    image_url = urljoin(url, image_url)
        
        # Extract main text
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        # We no longer truncate to 2000 characters. We return everything for chunking!
        return title.strip(), text, image_url
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return "", "", ""

def process_bookmark(a_tag):
    url = a_tag.get('href')
    title = a_tag.get_text(strip=True)
    if not url:
        return []
    print(f"Processing: {title} ({url})")
    
    page_title, page_text, image_url = fetch_content(url)
    
    chunks = chunk_text(page_text, chunk_size=500, overlap=50)
    
    results = []
    if not chunks:
        chunks = [""] # Ensure at least one chunk to index the title
        
    for i, chunk in enumerate(chunks):
        combined_text = f"Title: {title}\nPage Title: {page_title}\nContent: {chunk}"
        results.append({
            "id": f"{url}#chunk{i}",
            "text": combined_text,
            "metadata": {
                "title": title,
                "url": url,
                "image_url": image_url
            }
        })
        
    return results

def main():
    # To do a clean slate deep scan, we can reset the collection first.
    try:
        chroma_client.delete_collection("bookmarks")
        print("Deleted old bookmarks collection.")
    except Exception:
        pass
        
    global collection
    collection = chroma_client.get_or_create_collection(name="bookmarks", embedding_function=sentence_transformer_ef)

    with open('bookmarks.html', 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        
    a_tags = soup.find_all('a')
    print(f"Found {len(a_tags)} bookmarks.")
    
    documents = []
    metadatas = []
    ids = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_tag = {executor.submit(process_bookmark, tag): tag for tag in a_tags}
        for future in as_completed(future_to_tag):
            chunk_results = future.result()
            for result in chunk_results:
                if result and result['text'].strip():
                    documents.append(result['text'])
                    metadatas.append(result['metadata'])
                    ids.append(result['id'])
                
    if documents:
        unique_ids = set()
        deduped_docs = []
        deduped_metas = []
        deduped_ids = []
        
        # Deduplicate based on chunk ID just in case
        for d, m, idx in zip(documents, metadatas, ids):
            if idx not in unique_ids:
                unique_ids.add(idx)
                deduped_docs.append(d)
                deduped_metas.append(m)
                deduped_ids.append(idx)

        print(f"Inserting {len(deduped_docs)} chunks into ChromaDB...")
        
        # ChromaDB limits batch size, typically ~5000-40000 depending on config.
        # We will batch the upsert to avoid issues.
        batch_size = 5000
        for i in range(0, len(deduped_docs), batch_size):
            end = i + batch_size
            collection.upsert(
                documents=deduped_docs[i:end],
                metadatas=deduped_metas[i:end],
                ids=deduped_ids[i:end]
            )
            print(f"Inserted batch {i//batch_size + 1}...")
            
        print("Deep Scanning Insertion complete.")
    else:
        print("No valid documents found.")

if __name__ == '__main__':
    main()
