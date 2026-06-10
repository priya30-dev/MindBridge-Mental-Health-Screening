from datasets import load_dataset

dataset = load_dataset("dair-ai/emotion")

print(dataset)

dataset.save_to_disk("./data/raw/reddit")