from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import httpx

client = httpx.Client(verify=False)

import sqlite3


import os

llm = ChatOpenAI(
    base_url="https://genailab.tcs.in",
    model="azure/genailab-maas-gpt-4o-mini",
    api_key="sk-k-Q7fBGd_zzXOZpua5FduA", # Replace with your actual API key
    http_client=client
)

print("LLM instance created successfully")

embedding_model = OpenAIEmbeddings(
    base_url="https://genailab.tcs.in",
    model="azure/genailab-maas-text-embedding-3-large",
    api_key='sk-k-Q7fBGd_zzXOZpua5FduA', # Replace with your actual API key
    http_client=client
)

# print(llm.invoke("Hi! How are you?").content)
print(llm.invoke("List of berkshire poiciesk-mOrnO99I7SIj8OObMRoCBs for term life").content)