from huggingface_hub import InferenceClient


print("Enter the model that you want to test:")
print(" 1. Llama 3.1-8B")
print(" 2. GPT-OSS 20B")
print(" 3. Phi-4-mini-instruct")
print(" 4. All three models")

model = input("Enter your choice (1-4): ")

if model == "1":
    model_name = "meta-llama/Llama-3.1-8B-Instruct:fastest"
elif model == "2":
    model_name = "openai/gpt-oss-20b:fastest"
elif model == "3":
    model_name = "microsoft/Phi-4-mini-instruct:featherless-ai"
elif model == "4":
    model_name = ["meta-llama/Llama-3.1-8B-Instruct:fastest", "openai/gpt-oss-20b:fastest", "microsoft/Phi-4-mini-instruct:featherless-ai"]
else:
    print("Invalid choice. Please enter a number between 1 and 4.")
    exit(1)

token = input("Enter your Hugging Face API token: ")
question = input("Enter your question: ")

client = InferenceClient(
    api_key=token,
)

for current_model in (model_name if isinstance(model_name, list) else [model_name]):
    print(f"Model: {current_model}")

    completion = client.chat.completions.create(
        model=current_model, 
        messages=[
            {
                "role": "user",
                "content": question
            }
        ],
    )
    
    
    print(completion.choices[0].message)
