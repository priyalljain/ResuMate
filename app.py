import os
import sys
import pandas as pd
import gradio as gr
# Import your core main function directly for speed
from rank import main as run_rank_main  

def run_ranking(jd_text, uploaded_file):
    if uploaded_file is None:
        return None, "Error: Please upload a candidate pool file first!"

    candidates_in = uploaded_file.name 
    jd_path = "job_description.md"
    out_csv = "submission.csv"
    
    with open(jd_path, "w", encoding="utf-8") as f:
        f.write(jd_text)

    try:
        # 1. Mock terminal arguments in-memory (no slow subprocess.run!)
        original_argv = sys.argv
        sys.argv = [
            "rank.py",
            "--candidates", candidates_in,
            "--jd", jd_path,
            "--out", out_csv,
            "--shortlist-size", "500",  # Narrow the funnel to stay well under 5 mins on slow systems
            "--allow-short-pool"
        ]
        
        try:
            # 2. Run the main pipeline at native terminal speed
            run_rank_main()
        finally:
            sys.argv = original_argv
        
        # 3. Read generated output and extract top 100 entries safely
        if os.path.exists(out_csv):
            df = pd.read_csv(out_csv)
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str)
            return df.head(100), "Success! Pipeline executed natively in memory."
        else:
            return None, "Pipeline completed but submission.csv was not found."
            
    except Exception as e:
        return None, f"Pipeline Error:\n{str(e)}"

# Build the custom themed dashboard interface (Moved theme from here)
with gr.Blocks(title="Redrob AI Talent Intelligence Engine") as demo:
    gr.Markdown("# Redrob AI Talent Intelligence Ranker Dashboard")
    
    with gr.Row():
        with gr.Column(scale=2):
            file_input = gr.File(label="Upload Candidate Pool (.jsonl or .jsonl.gz)", file_types=[".jsonl", ".gz"])
            jd_input = gr.Textbox(label="Job Description (Markdown format)", lines=10, value="# Job Description...")
            submit_btn = gr.Button("Run Ranking Funnel Engine", variant="primary", elem_id="purple_button")
            
        with gr.Column(scale=3):
            status_output = gr.Textbox(label="Execution Logs", lines=4)
            # FIXED: Removed overflow_row_behaviour for Gradio 6.0 compliance
            file_output = gr.DataFrame(label="Top 100 Ranked Shortlist Preview", interactive=False)

    # Pure black styling configuration
    demo.css = """
    body, .gradio-container, html { background-color: #000000 !important; color: #FFFFFF !important; }
    textarea, input, .table-wrap, .dataframe { background-color: #111111 !important; color: #FFFFFF !important; }
    #purple_button { background-color: #7C3AED !important; color: #FFFFFF !important; font-weight: 600 !important; }
    footer { display: none !important; }
    """

    submit_btn.click(fn=run_ranking, inputs=[jd_input, file_input], outputs=[file_output, status_output])

if __name__ == "__main__":
    # FIXED: Passed theme configuration parameters directly inside launch() instead
    demo.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Default())