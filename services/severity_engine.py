import pandas as pd

class SeverityEngine:
    def __init__(self, csv_path="data/severity_weight.csv"):
        df = pd.read_csv(csv_path)
        self.weights = dict(zip(df.symptom, df.weight))

    def calculate(self, symptoms):
        score = sum(self.weights.get(s, 0) for s in symptoms)

        if score < 3:
            level = "low"
        elif score < 6:
            level = "medium"
        else:
            level = "high"

        return score, level
