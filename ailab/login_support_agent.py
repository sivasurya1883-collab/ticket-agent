import streamlit as st
from langchain_openai import ChatOpenAI
import httpx
import sqlite3

# Set up the HTTP client (disable SSL verification for demo purposes)
client = httpx.Client(verify=False)

# Initialize the LLM with your API details
def get_llm():
    return ChatOpenAI(
        base_url="https://genailab.tcs.in",
        model="azure/genailab-maas-gpt-4o-mini",
        api_key="sk-k-Q7fBGd_zzXOZpua5FduA",
        http_client=client
    )

def init_db():
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_query TEXT,
        response TEXT,
        status TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

st.title("Login Issue Support Agent")
st.write("Ask me anything about issues you're facing logging in to the application.")

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

user_input = st.text_input("Your login issue:")

if st.button("Ask") and user_input:
    # Agent 1: Create ticket
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    c.execute("INSERT INTO tickets (user_query, response, status) VALUES (?, ?, ?)", (user_input, '', 'open'))
    conn.commit()
    conn.close()
    st.session_state['chat_history'].append((user_input, "Ticket created. Awaiting support agent response."))

if st.button("Process Tickets (Support Agent)"):
    # Agent 2: Solve tickets
    conn = sqlite3.connect('tickets.db')
    c = conn.cursor()
    c.execute("SELECT id, user_query FROM tickets WHERE status = 'open'")
    tickets = c.fetchall()
    llm = get_llm()
    for ticket_id, query in tickets:
        prompt = f"A user is facing a login issue. Their query: '{query}'. Please provide a helpful, step-by-step troubleshooting response."
        response = llm.invoke(prompt).content
        c.execute("UPDATE tickets SET response = ?, status = 'solved' WHERE id = ?", (response, ticket_id))
        st.session_state['chat_history'].append((query, response))
    conn.commit()
    conn.close()

# Display chat history
for i, (q, a) in enumerate(reversed(st.session_state['chat_history'])):
    st.markdown(f"**You:** {q}")
    st.markdown(f"**Agent:** {a}")
