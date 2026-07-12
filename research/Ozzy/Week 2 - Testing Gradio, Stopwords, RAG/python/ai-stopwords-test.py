import gradio as gr
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download('stopwords')
nltk.download('punkt')
nltk.download('punkt_tab')

def remove_stopwords(text):
    stop_words = set(stopwords.words('english'))
    tokens = word_tokenize(text)
    filtered_tokens = [word for word in tokens if word not in stop_words]
    return tokens, filtered_tokens, len(tokens), len(filtered_tokens)
    

with gr.Blocks() as demo:
    title = gr.Markdown(
            '''
            # Stopwords Removal Demo
            '''
            )
    
    with gr.Row():
        input_text = gr.Textbox(label="Input Text", placeholder="Enter text to remove stopwords...")
        output_text = gr.Textbox(label="Output Text", placeholder="Stopwords removed text will appear here...")
    
    with gr.Row():
        original_tokens = gr.Textbox(label="Original Tokens", placeholder="Tokens before stopwords removal...")
        filtered_tokens = gr.Textbox(label="Filtered Tokens", placeholder="Tokens after stopwords removal...")
        
    with gr.Row():
        original_count = gr.Textbox(label="Original Token Count", placeholder="Number of tokens before stopwords removal...")
        filtered_count = gr.Textbox(label="Filtered Token Count", placeholder="Number of tokens after stopwords removal...")
    
    remove_btn = gr.Button("Remove Stopwords")
    remove_btn.click(fn=remove_stopwords, inputs=input_text, outputs=[output_text, original_tokens, filtered_tokens, original_count, filtered_count])
    
demo.launch()