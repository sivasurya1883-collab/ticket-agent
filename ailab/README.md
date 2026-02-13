# Multi-Agent Ticket Resolution Chat App

## What this is

A Streamlit chat app that uses LangGraph to orchestrate a multi-agent workflow for login-related support tickets.

- **Conversation agent**: detects login/auth issues and drafts a ticket.
- **Ticket resolution agent**: looks for similar closed tickets (your history first, then other users), otherwise asks clarifying questions or generates a new solution.
- **Similarity search**: OpenAI-compatible embeddings + in-memory FAISS.
- **Database**: Supabase Postgres tables `users` and `tickets`.

## Project layout

- `app.py` Streamlit UI (login + chat + sidebar)
- `support_app/`
  - `config.py` env loading + settings
  - `db.py` Supabase data access for `users` / `tickets`
  - `llm.py` OpenAI-compatible LLM + embeddings
  - `agents.py` conversation + resolution prompt logic (structured outputs)
  - `similarity.py` FAISS similarity index over closed tickets
  - `graph.py` LangGraph orchestration (nodes + flow)
- `supabase/schema.sql` table DDL
- `supabase/seed.sql` mock data (15 users, 45 tickets)

## Supabase setup

1. Create a Supabase project.
2. In **SQL Editor**, run:

- `supabase/schema.sql`
- `supabase/seed.sql`

This seeds users and tickets (mix of `Open`, `In Progress`, and `Closed`).

## Environment variables

Create a `.env` file in the repo root (or set env vars in your shell):

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENAI_API_KEY`

Optional:

- `OPENAI_BASE_URL` (if using an OpenAI-compatible gateway)
- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `OPENAI_EMBEDDINGS_MODEL` (default: `text-embedding-3-large`)
- `SIMILARITY_THRESHOLD` (FAISS distance threshold, default `0.82`; lower is stricter)

## Install + run

Python 3.11+

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then login using any seeded user, for example:

- `aisha.khan` / `Pass@123`
- `rohan.sharma` / `Welcome@123`

## Trigger mechanism (Supabase trigger simulation)

This implementation uses **direct invocation inside the LangGraph flow**:

- When the conversation agent decides a ticket is needed, the graph runs `ticket_creation_node` which inserts into Supabase.
- Immediately after insert, the graph proceeds to `ticket_resolution_agent` + `similarity_check` and returns a solution back to the conversation.

This provides a deterministic “trigger-like” behavior without needing DB triggers/webhooks.

### Optional polling mode (future)

If you want a more realistic async trigger:

- Run a background polling worker that periodically queries `tickets` where `status='Open'`.
- For each ticket, run the resolution sub-graph and update the ticket to `Closed`.

(Worker not implemented yet in this repo.)
