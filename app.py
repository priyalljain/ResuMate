import os
import subprocess
import pandas as pd
import gradio as gr

def run_ranking(jd_text):
    # 1. Save the job description input to disk
    jd_path = "current_jd.md"
    with open(jd_path, "w", encoding="utf-8") as f:
        f.write(jd_text)
        
    # 2. Use your existing sample fixtures as the mock data pool
    candidates_in = "tests/fixtures/sample_candidates.json" 
    out_csv = "submission.csv"
    
    if not os.path.exists(candidates_in):
        return None, f"Error: Data pool fixture file not found at '{candidates_in}'."

    try:
        # 3. Call your core rank.py pipeline exactly as it is built
        cmd = [
            "python", "rank.py",
            "--candidates", candidates_in,
            "--jd", jd_path,
            "--out", out_csv,
            "--allow-short-pool"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # 4. Read generated submission output to preview in the Gradio dashboard
        if os.path.exists(out_csv):
            df = pd.read_csv(out_csv)
            return df, f"Success!\n\nPipeline Output:\n{result.stdout}"
        else:
            return None, f"Pipeline completed but submission.csv was not found.\nLog:\n{result.stderr}"
            
    except subprocess.CalledProcessError as e:
        return None, f"Pipeline Error:\n{e.stderr}\n{e.stdout}"

# Build the custom Dark Purple themed dashboard interface
with gr.Blocks(theme=gr.themes.Default(), title="Redrob AI Talent Intelligence Engine") as demo:
    gr.Markdown("# Redrob AI Talent Intelligence Ranker Dashboard")
    gr.Markdown("Modify the job description below to test the Cascading Funnel Architecture processing pool pipeline.")
    
    with gr.Row():
        with gr.Column(scale=2):
            jd_input = gr.Textbox(
                label="Job Description (Markdown format)", 
                lines=12, 
                value="""# Job Description: Senior AI Engineer
**Experience Required:** 4–7 years

## Requirements
Looking for an engineer experienced in information retrieval, semantic search, dense vector embeddings, and all-MiniLM-L6-v2."""
            )
            submit_btn = gr.Button(
                "Run Ranking Funnel Engine", 
                variant="primary",
                elem_id="purple_button"
            )
            
        with gr.Column(scale=3):
            status_output = gr.Textbox(label="Execution Logs", lines=4)
            file_output = gr.DataFrame(label="Ranked Shortlist Preview")

    # Embedded CSS for Dark Theme layout with Royal Purple accents
    demo.css = """
    body, .gradio-container {
        background-color: #090D16 !important;
        color: #F3F4F6 !important;
    }
    .markdown-text * {
        color: #F3F4F6 !important;
    }
    #purple_button {
        background-color: #7C3AED !important; 
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 6px !important;
        transition: background 0.2s ease;
    }
    #purple_button:hover {
        background-color: #6D28D9 !important;
    }
    footer {
        display: none !important;
    }
    """

    submit_btn.click(
        fn=run_ranking,
        inputs=[jd_input],
        outputs=[file_output, status_output]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)