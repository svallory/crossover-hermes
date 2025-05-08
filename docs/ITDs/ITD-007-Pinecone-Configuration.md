# ITD-007: Pinecone Configuration for Hermes PoC

**Date:** 2024-07-29
**Author:** Gemini Assistant
**Status:** Revised

## 1. Context

Following the selection of Pinecone as our vector database (ITD-001) and OpenAI's `text-embedding-3-small` as our embedding model (ITD-002), this document outlines the specific configuration and implementation details for Pinecone integration. We need to define the index structure, metadata schema, and query approaches to ensure effective RAG functionality for product inquiries.

## 2. Requirements

* **Scalability:** Handle product embeddings for the PoC catalog
* **Performance:** Fast similarity search for inquiry responses
* **Metadata Support:** Store relevant product information alongside vectors
* **Simplicity:** Focus on core functionality needed for the PoC

## 3. Pinecone Index Configuration

### 3.1 Index Parameters

* **Index Name:** `hermes-products`
* **Dimensions:** 1536 (matching `text-embedding-3-small` output)
* **Metric:** `cosine` (most suitable for semantic similarity with normalized embeddings)
* **Pod Type:** `p1.x1` (smallest pod size, suitable for PoC within free tier)

### 3.2 Metadata Schema

The following metadata fields will be stored with each vector:

```python
metadata = {
    "product_id": str,      # Unique identifier
    "name": str,            # Product name
    "description": str,     # Product description
    "category": str,        # Product category
    "season": str,          # Applicable season
    "price": float,         # Product price
    "stock": int            # Current stock level
}
```

## 4. Embedding Strategy

### 4.1 Text Preparation

For each product, we'll create a combined text representation by concatenating relevant fields:

```python
def prepare_embedding_text(product):
    return f"Product: {product['name']}\n" \
           f"Description: {product['description']}\n" \
           f"Category: {product['category']}\n" \
           f"Season: {product['season']}"
```

### 4.2 Batch Processing

To optimize API calls:

* Process embeddings in batches (e.g., 20 products per batch)
* Add brief delays between batch requests if needed

## 5. Upsert Implementation

For the population of the vector store:

```python
def populate_pinecone(products_df, batch_size=20):
    # Initialize Pinecone
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
    
    # Create index if it doesn't exist
    if "hermes-products" not in pinecone.list_indexes():
        pinecone.create_index(
            name="hermes-products",
            dimension=1536,
            metric="cosine"
        )
    
    # Connect to index
    index = pinecone.Index("hermes-products")
    
    # Process products in batches
    for i in range(0, len(products_df), batch_size):
        batch = products_df.iloc[i:i+batch_size]
        
        # Prepare texts for embedding
        texts = [prepare_embedding_text(row) for _, row in batch.iterrows()]
        
        # Generate embeddings with OpenAI
        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        embeddings = [item.embedding for item in response.data]
        
        # Prepare vectors with metadata
        vectors = []
        for j, (_, product) in enumerate(batch.iterrows()):
            vector = {
                "id": product["product_id"],
                "values": embeddings[j],
                "metadata": {
                    "product_id": product["product_id"],
                    "name": product["name"],
                    "description": product["description"],
                    "category": product["category"],
                    "season": product["season"],
                    "price": float(product["price"]),
                    "stock": int(product["stock"])
                }
            }
            vectors.append(vector)
        
        # Upsert batch to Pinecone
        index.upsert(vectors=vectors)
        
    return index
```

## 6. Query Implementation

For handling product inquiries:

```python
def query_products(query_text, top_k=3):
    # Get the index
    index = pinecone.Index("hermes-products")
    
    # Generate embedding for query
    response = client.embeddings.create(
        input=query_text,
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding
    
    # Query Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )
    
    return results
```

## 7. Basic Error Handling

Include simple error handling for essential operations:

```python
def safe_query_products(query_text, top_k=3):
    try:
        return query_products(query_text, top_k)
    except Exception as e:
        print(f"Error querying products: {e}")
        # Return empty results as fallback
        return {"matches": []}
```

## 8. Implementation Sequence

1. Set up Pinecone client with API key
2. Create index with specified configuration
3. Process product catalog and upload embeddings
4. Implement basic query function
5. Integrate with inquiry processing logic

## 9. Next Steps

1. Implement the embedding and upsert pipeline
2. Test embedding quality with sample product descriptions
3. Create query interface for inquiry handling
4. Integrate with the inquiry response prompt 