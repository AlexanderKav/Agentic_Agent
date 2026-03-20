import os

def __init__(self, output_dir="agents/charts"):
    self.output_dir = os.path.abspath(output_dir)
    os.makedirs(self.output_dir, exist_ok=True)
    print("Charts will be saved to:", self.output_dir)  # ← This should be there