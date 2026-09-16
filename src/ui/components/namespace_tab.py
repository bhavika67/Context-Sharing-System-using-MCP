"""
components/namespace_tab.py — 🗃️ Domains tab
"""

import gradio as gr

from api_client.context import list_domains, share_memory, clear_domain


def build(app: gr.Blocks) -> None:
    """Render the Domains tab. Call inside a gr.Tab() context.

    Parameters
    ----------
    app:
        The top-level gr.Blocks instance, needed to register app.load handlers.
    """
    gr.Markdown("### All domains")
    dom_table = gr.Dataframe(
        headers=["domain", "entries"],
        datatype=["str", "number"],
        interactive=False,
    )
    refresh_dom_btn = gr.Button("Refresh")

    gr.Markdown("### Share memory between domains")
    with gr.Row():
        share_con    = gr.Textbox(label="Concept to share")
        share_src    = gr.Textbox(label="Source domain")
        share_dst    = gr.Textbox(label="Target domain")
        share_newcon = gr.Textbox(label="New concept name (optional)")
    share_btn = gr.Button("Share", variant="primary")
    share_out = gr.Textbox(label="Result", interactive=False)

    gr.Markdown("### Clear domain")
    with gr.Row():
        clear_dom_input = gr.Textbox(label="Domain to clear")
        clear_dom_btn   = gr.Button("Clear all entries", variant="stop")
    clear_dom_out = gr.Textbox(label="Result", interactive=False)

    # ── Wire up events ────────────────────────────────────────────────────────
    refresh_dom_btn.click(list_domains, outputs=dom_table)
    share_btn.click(share_memory, [share_con, share_src, share_dst, share_newcon], share_out)
    clear_dom_btn.click(clear_domain, [clear_dom_input], clear_dom_out)
    app.load(list_domains, outputs=dom_table)
