# Hermes: AI-Powered Email Processing System for Fashion Retail

## Overview
This solution processes customer emails for a fashion store, classifying them as either product inquiries or order requests, then generating appropriate responses using product catalog information and current stock status.

## Implementation Plan
1. Environment setup (dependencies, API keys)
2. Data loading and exploration
3. Email classification
4. Order request processing and stock management
5. Product inquiry handling using RAG
6. Response generation with appropriate tone
7. Output preparation

## 1. Environment Setup

~~~python
# Required imports
import pandas as pd
import numpy as np
from openai import OpenAI
import os
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import List, Dict, Tuple, Any, Optional

# Configure OpenAI client
client = OpenAI(
    base_url='https://47v4us7kyypinfb5lcligtc3x40ygqbs.lambda-url.us-east-1.on.aws/v1/',
    api_key='sk-crossover-temp-key'  # Replace with actual key or your own
)

# Input data source
INPUT_SPREADSHEET_ID = '14fKHsblfqZfWj3iAaM2oA51TlYfQlFT4WKo52fVaQ9U'

# Function to read data from Google Sheets
def read_data_frame(document_id, sheet_name):
    export_link = f"https://docs.google.com/spreadsheets/d/{document_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(export_link)
~~~

## 2. Data Loading and Exploration

~~~python
# Load product and email data
products_df = read_data_frame(INPUT_SPREADSHEET_ID, 'products')
emails_df = read_data_frame(INPUT_SPREADSHEET_ID, 'emails')

# Display sample data
print("Products sample:")
print(products_df.head(3))
print("\nEmails sample:")
print(emails_df.head(3))

# Check data dimensions
print(f"\nProducts dataset shape: {products_df.shape}")
print(f"Emails dataset shape: {emails_df.shape}")
~~~

## 3. Email Classification

For email classification, I'll use a zero-shot approach with GPT-4o to determine if an email is a product inquiry or an order request.

~~~python
def classify_email(email_subject, email_body):
    """
    Classify an email as either a 'product inquiry' or an 'order request'
    
    Args:
        email_subject (str): The subject of the email
        email_body (str): The body content of the email
        
    Returns:
        str: Classification - either 'product inquiry' or 'order request'
    """
    prompt = f"""
    You are an AI assistant for a fashion store. Classify the following email as either a 'product inquiry' or an 'order request'.
    
    Email Subject: {email_subject}
    Email Body: {email_body}
    
    Only respond with exactly one of these two categories: 'product inquiry' or 'order request'
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that classifies fashion store emails."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )
    
    classification = response.choices[0].message.content.strip().lower()
    
    # Ensure the response is valid (either 'product inquiry' or 'order request')
    if classification not in ['product inquiry', 'order request']:
        # If invalid response, default to most likely classification based on keywords
        if any(word in email_body.lower() for word in ['order', 'purchase', 'buy', 'payment']):
            classification = 'order request'
        else:
            classification = 'product inquiry'
    
    return classification

# Process all emails and store classifications
def classify_all_emails(emails_df):
    """
    Classify all emails in the DataFrame
    
    Args:
        emails_df (DataFrame): DataFrame containing email data
        
    Returns:
        DataFrame: DataFrame with email IDs and classifications
    """
    results = []
    
    for _, row in emails_df.iterrows():
        email_id = row['email ID']
        subject = row['subject']
        body = row['body']
        
        classification = classify_email(subject, body)
        results.append({
            'email ID': email_id,
            'category': classification
        })
        print(f"Classified email {email_id} as: {classification}")
    
    return pd.DataFrame(results)

# Generate email classifications
email_classification_df = classify_all_emails(emails_df)
~~~

## 4. Order Request Processing

Now I'll implement the order processing logic, which includes checking stock, updating inventory, and recording order status.

~~~python
def extract_order_details(email_body, products_df):
    """
    Extract product IDs and quantities from an order request email
    
    Args:
        email_body (str): Content of the email
        products_df (DataFrame): Product catalog with product details
        
    Returns:
        list: List of dictionaries containing product ID and quantity
    """
    # Create a context with product information to help the LLM extract orders accurately
    product_context = "Available products:\n"
    for _, product in products_df.iterrows():
        product_context += f"ID: {product['product ID']}, Name: {product['name']}\n"
    
    # Truncate if needed to stay within token limits
    if len(product_context) > 2000:
        product_context = product_context[:2000] + "...(more products available)"
    
    prompt = f"""
    Extract the order details from the following email. For each product being ordered, identify the product ID and quantity.
    
    {product_context}
    
    Email: {email_body}
    
    Return a JSON array of objects with 'product_id' and 'quantity' fields. Only include products that are being ordered.
    Example: [{{"product_id": "P001", "quantity": 2}}, {{"product_id": "P002", "quantity": 1}}]
    
    If no specific product IDs are mentioned, try to match product names to the catalog.
    If quantities aren't specified, assume a quantity of 1.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You extract order information from emails for a fashion store."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    try:
        result = response.choices[0].message.content
        order_items = eval(result)["0" if "0" in result else 0] if isinstance(result, str) and len(result) > 0 else []
        
        # Convert to expected format if needed
        processed_items = []
        for item in order_items:
            processed_items.append({
                'product_id': item.get('product_id', ''),
                'quantity': int(item.get('quantity', 1))
            })
        
        return processed_items
    except Exception as e:
        print(f"Error extracting order details: {e}")
        return []

def process_order(email_id, email_body, products_df):
    """
    Process an order request and update stock levels
    
    Args:
        email_id (str): ID of the email
        email_body (str): Content of the email
        products_df (DataFrame): Product catalog with stock information
        
    Returns:
        tuple: (order_status_records, updated_products_df)
    """
    order_items = extract_order_details(email_body, products_df)
    order_status_records = []
    
    # Create a copy of the products DataFrame to update stock levels
    updated_products_df = products_df.copy()
    
    for item in order_items:
        product_id = item['product_id']
        quantity = item['quantity']
        
        # Find the product in the catalog
        product_mask = updated_products_df['product ID'] == product_id
        if not any(product_mask):
            # Product not found in catalog
            order_status_records.append({
                'email ID': email_id,
                'product ID': product_id,
                'quantity': quantity,
                'status': 'out of stock'  # Product not found is treated as out of stock
            })
            continue
        
        current_stock = updated_products_df.loc[product_mask, 'stock'].iloc[0]
        
        if current_stock >= quantity:
            # Order can be fulfilled
            order_status_records.append({
                'email ID': email_id,
                'product ID': product_id,
                'quantity': quantity,
                'status': 'created'
            })
            
            # Update stock level
            updated_products_df.loc[product_mask, 'stock'] -= quantity
        else:
            # Insufficient stock
            order_status_records.append({
                'email ID': email_id,
                'product ID': product_id,
                'quantity': quantity,
                'status': 'out of stock'
            })
    
    return order_status_records, updated_products_df

def process_all_orders(emails_df, email_classification_df, products_df):
    """
    Process all order request emails
    
    Args:
        emails_df (DataFrame): DataFrame containing email data
        email_classification_df (DataFrame): DataFrame with email classifications
        products_df (DataFrame): Product catalog with stock information
        
    Returns:
        tuple: (order_status_df, updated_products_df)
    """
    order_status_records = []
    updated_products_df = products_df.copy()
    
    # Filter to get only order request emails
    order_emails = emails_df.merge(
        email_classification_df[email_classification_df['category'] == 'order request'],
        on='email ID'
    )
    
    for _, row in order_emails.iterrows():
        email_id = row['email ID']
        email_body = row['body']
        
        records, updated_products_df = process_order(email_id, email_body, updated_products_df)
        order_status_records.extend(records)
        
        print(f"Processed order in email {email_id}: {len(records)} items")
    
    return pd.DataFrame(order_status_records), updated_products_df

# Process all orders
order_status_df, updated_products_df = process_all_orders(emails_df, email_classification_df, products_df)
~~~

## 5. Product Inquiry Handling with RAG

For product inquiries, I'll implement a RAG system to find relevant products and generate helpful responses.

~~~python
def get_product_embeddings(products_df):
    """
    Generate embeddings for all products in the catalog
    
    Args:
        products_df (DataFrame): Product catalog
        
    Returns:
        tuple: (list of product embeddings, list of product info dictionaries)
    """
    product_embeddings = []
    product_info = []
    
    for _, product in products_df.iterrows():
        # Create a comprehensive text representation of the product
        product_text = f"Product ID: {product['product ID']}\n" \
                       f"Name: {product['name']}\n" \
                       f"Category: {product['category']}\n" \
                       f"Stock: {product['stock']}\n" \
                       f"Description: {product['description']}\n" \
                       f"Season: {product['season']}"
        
        # Get embedding for the product text
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=product_text
        )
        
        embedding = response.data[0].embedding
        product_embeddings.append(embedding)
        
        # Store product info for retrieval
        product_info.append({
            'product_id': product['product ID'],
            'name': product['name'],
            'category': product['category'],
            'stock': product['stock'],
            'description': product['description'],
            'season': product['season'],
            'text': product_text
        })
    
    return product_embeddings, product_info

def get_query_embedding(query_text):
    """
    Generate embedding for a query
    
    Args:
        query_text (str): Query text
        
    Returns:
        list: Embedding vector
    """
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=query_text
    )
    
    return response.data[0].embedding

def retrieve_relevant_products(query_text, product_embeddings, product_info, top_k=3):
    """
    Retrieve the most relevant products for a query using embeddings
    
    Args:
        query_text (str): Query text
        product_embeddings (list): List of product embeddings
        product_info (list): List of product info dictionaries
        top_k (int): Number of products to retrieve
        
    Returns:
        list: Most relevant products
    """
    query_embedding = get_query_embedding(query_text)
    
    # Calculate cosine similarity between query and all products
    query_embedding_array = np.array([query_embedding])
    product_embeddings_array = np.array(product_embeddings)
    
    similarities = cosine_similarity(query_embedding_array, product_embeddings_array)[0]
    
    # Get indices of top_k most similar products
    top_indices = similarities.argsort()[-top_k:][::-1]
    
    # Return the most relevant products with their similarity scores
    relevant_products = []
    for idx in top_indices:
        relevant_products.append({
            **product_info[idx],
            'similarity_score': similarities[idx]
        })
    
    return relevant_products

def generate_inquiry_response(email_body, products_df):
    """
    Generate a response to a product inquiry using RAG
    
    Args:
        email_body (str): Email content
        products_df (DataFrame): Product catalog
        
    Returns:
        str: Generated response
    """
    # Get product embeddings and info (in practice, this would be done once and cached)
    product_embeddings, product_info = get_product_embeddings(products_df)
    
    # Retrieve relevant products
    relevant_products = retrieve_relevant_products(email_body, product_embeddings, product_info)
    
    # Format product information for the prompt
    product_context = "Relevant products:\n\n"
    for product in relevant_products:
        product_context += f"Product ID: {product['product_id']}\n"
        product_context += f"Name: {product['name']}\n"
        product_context += f"Category: {product['category']}\n"
        product_context += f"Stock: {product['stock']}\n"
        product_context += f"Description: {product['description']}\n"
        product_context += f"Season: {product['season']}\n\n"
    
    prompt = f"""
    You are a customer service representative for a fashion store. Generate a friendly, professional response to the following customer inquiry.
    Use only the product information provided below. If the information doesn't fully answer the customer's question, acknowledge that
    and offer to provide more details or connect them with a specialist.
    
    Customer inquiry: {email_body}
    
    {product_context}
    
    Your response should be professional, helpful, and not too lengthy. Focus on addressing the customer's specific questions.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful customer service assistant for a fashion store."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content

def handle_all_inquiries(emails_df, email_classification_df, products_df):
    """
    Process all product inquiry emails
    
    Args:
        emails_df (DataFrame): DataFrame containing email data
        email_classification_df (DataFrame): DataFrame with email classifications
        products_df (DataFrame): Product catalog
        
    Returns:
        DataFrame: DataFrame with email IDs and responses
    """
    inquiry_response_records = []
    
    # Filter to get only product inquiry emails
    inquiry_emails = emails_df.merge(
        email_classification_df[email_classification_df['category'] == 'product inquiry'],
        on='email ID'
    )
    
    for _, row in inquiry_emails.iterrows():
        email_id = row['email ID']
        email_body = row['body']
        
        response = generate_inquiry_response(email_body, products_df)
        
        inquiry_response_records.append({
            'email ID': email_id,
            'response': response
        })
        
        print(f"Generated response for inquiry email {email_id}")
    
    return pd.DataFrame(inquiry_response_records)

# Process all product inquiries
inquiry_response_df = handle_all_inquiries(emails_df, email_classification_df, products_df)
~~~

## 6. Order Response Generation

Now I'll generate appropriate responses for order requests based on their status.

~~~python
def generate_order_response(email_id, email_body, order_status_records, products_df):
    """
    Generate a response for an order request
    
    Args:
        email_id (str): Email ID
        email_body (str): Email content
        order_status_records (list): List of order status records for this email
        products_df (DataFrame): Product catalog
        
    Returns:
        str: Generated response
    """
    # Group order items by status
    created_items = []
    out_of_stock_items = []
    
    for record in order_status_records:
        if record['email ID'] != email_id:
            continue
            
        product_id = record['product ID']
        quantity = record['quantity']
        status = record['status']
        
        # Get product details
        product_mask = products_df['product ID'] == product_id
        if not any(product_mask):
            product_name = f"Product {product_id}"
            product_category = "Unknown"
        else:
            product = products_df[product_mask].iloc[0]
            product_name = product['name']
            product_category = product['category']
        
        item_info = {
            'product_id': product_id,
            'name': product_name,
            'category': product_category,
            'quantity': quantity
        }
        
        if status == 'created':
            created_items.append(item_info)
        else:
            out_of_stock_items.append(item_info)
    
    # Format order items for the prompt
    created_items_text = ""
    for item in created_items:
        created_items_text += f"- {item['quantity']}x {item['name']} (ID: {item['product_id']})\n"
    
    out_of_stock_items_text = ""
    for item in out_of_stock_items:
        out_of_stock_items_text += f"- {item['quantity']}x {item['name']} (ID: {item['product_id']})\n"
    
    # Find alternative products for out-of-stock items
    alternatives_text = ""
    if out_of_stock_items:
        for item in out_of_stock_items:
            category = item['category']
            similar_products = products_df[
                (products_df['category'] == category) & 
                (products_df['stock'] > 0) &
                (products_df['product ID'] != item['product_id'])
            ].head(2)
            
            if not similar_products.empty:
                alternatives_text += f"For {item['name']} (ID: {item['product_id']}), we recommend:\n"
                for _, alt in similar_products.iterrows():
                    alternatives_text += f"- {alt['name']} (ID: {alt['product ID']}, stock: {alt['stock']})\n"
    
    prompt = f"""
    You are a customer service representative for a fashion store. Generate a professional response to a customer's order request.
    
    Customer's email: {email_body}
    
    Items available and processed:
    {created_items_text if created_items_text else "None"}
    
    Items out of stock:
    {out_of_stock_items_text if out_of_stock_items_text else "None"}
    
    Alternative products available:
    {alternatives_text if alternatives_text else "No alternatives found."}
    
    Consider the following in your response:
    1. If all items are available, confirm the order and provide a summary of the items.
    2. If some items are out of stock, acknowledge this and inform about the items that are available.
    3. If all items are out of stock, apologize and suggest alternatives if available.
    4. Maintain a professional, friendly tone throughout.
    
    Your response should be concise, helpful, and production-ready.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful customer service assistant for a fashion store."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content

def generate_all_order_responses(emails_df, email_classification_df, order_status_df, products_df):
    """
    Generate responses for all order request emails
    
    Args:
        emails_df (DataFrame): DataFrame containing email data
        email_classification_df (DataFrame): DataFrame with email classifications
        order_status_df (DataFrame): DataFrame with order status records
        products_df (DataFrame): Product catalog
        
    Returns:
        DataFrame: DataFrame with email IDs and responses
    """
    order_response_records = []
    
    # Filter to get only order request emails
    order_emails = emails_df.merge(
        email_classification_df[email_classification_df['category'] == 'order request'],
        on='email ID'
    )
    
    for _, row in order_emails.iterrows():
        email_id = row['email ID']
        email_body = row['body']
        
        # Get order status records for this email
        email_orders = order_status_df[order_status_df['email ID'] == email_id].to_dict('records')
        
        response = generate_order_response(email_id, email_body, email_orders, products_df)
        
        order_response_records.append({
            'email ID': email_id,
            'response': response
        })
        
        print(f"Generated response for order email {email_id}")
    
    return pd.DataFrame(order_response_records)

# Generate responses for all orders
order_response_df = generate_all_order_responses(emails_df, email_classification_df, order_status_df, products_df)
~~~

## 7. Complete System Integration

Now I'll integrate all components into a complete workflow and prepare the final output format.

~~~python
def process_emails_pipeline():
    """
    Process all emails through the complete pipeline
    """
    print("1. Loading data...")
    products_df = read_data_frame(INPUT_SPREADSHEET_ID, 'products')
    emails_df = read_data_frame(INPUT_SPREADSHEET_ID, 'emails')
    
    print("2. Classifying emails...")
    email_classification_df = classify_all_emails(emails_df)
    
    print("3. Processing order requests...")
    order_status_df, updated_products_df = process_all_orders(emails_df, email_classification_df, products_df)
    
    print("4. Generating order responses...")
    order_response_df = generate_all_order_responses(emails_df, email_classification_df, order_status_df, products_df)
    
    print("5. Handling product inquiries...")
    inquiry_response_df = handle_all_inquiries(emails_df, email_classification_df, products_df)
    
    print("6. Pipeline complete!")
    
    return {
        'email_classification': email_classification_df,
        'order_status': order_status_df,
        'order_response': order_response_df,
        'inquiry_response': inquiry_response_df,
        'updated_products': updated_products_df
    }

# Run the complete pipeline
results = process_emails_pipeline()

# Display sample outputs
print("\nSample outputs:")
print("\nEmail Classification:")
print(results['email_classification'].head())

print("\nOrder Status:")
print(results['order_status'].head())

print("\nOrder Response:")
print(results['order_response'].head(1))

print("\nInquiry Response:")
print(results['inquiry_response'].head(1))
~~~

## Conclusion

This solution implements a complete AI-powered email processing system for a fashion store, using advanced techniques like:

1. **LLM-based classification** to categorize emails accurately
2. **Order processing** with stock verification and management
3. **RAG implementation** for product inquiries to ensure scalability with large catalogs
4. **Appropriate tone adaptation** in generated responses

The system is designed to be scalable, handling a potentially large product catalog without exceeding token limits by using embedding-based retrieval rather than including the entire catalog in prompts.

All requirements have been implemented:
- Email classification
- Order processing with stock management
- Appropriate response generation for both order requests and product inquiries

The code is structured to be maintainable and follows best practices for AI and LLM tool usage. 