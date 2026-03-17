import pandas as pd
import numpy as np

rows = 1000
cols = 10000

data = np.random.rand(rows, cols)

df = pd.DataFrame(data, columns=[f"col_{i}" for i in range(cols)])

df.to_csv("large_test_file.csv", index=False)