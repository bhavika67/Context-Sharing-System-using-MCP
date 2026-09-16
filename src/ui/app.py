"""
app.py — Gradio UI entry point
───────────────────────────────
Architecture:
    Gradio UI → FastAPI (port 8000) → MCP Server → SQLite

Module layout:
    api_client/http.py          — raw GET / POST / DELETE
    api_client/context.py       — memory + domain API calls
    api_client/chat.py          — chat + stats API calls
    components/chat_tab.py      — Chat tab
    components/context_tab.py   — Memory Manager tab
    components/namespace_tab.py — Domains tab
    components/stats_tab.py     — Stats tab

Run:
    python src/ui/app.py
"""

import gradio as gr

from components import chat_tab, context_tab, namespace_tab, stats_tab

with gr.Blocks(title="MCP Project Memory") as app:

    gr.Markdown("# MCP Project Memory System")
    gr.Markdown(
        "**Architecture:** Gradio UI → FastAPI (port 8000) → MCP Server → SQLite  \n"
        "**Stack:** OpenAI · MCP · FastAPI · Gradio"
    )

    with gr.Tabs():
        with gr.Tab("Chat"):
            chat_tab.build()

        with gr.Tab("Memory Manager"):
            context_tab.build()

        with gr.Tab("Domains"):
            namespace_tab.build(app)

        with gr.Tab("Stats"):
            stats_tab.build(app)


if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Soft(),
    )
