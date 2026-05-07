import pandas as pd

class SeverityEngine:
    def __init__(self, csv_path="data/severity_weight.csv"):
        df = pd.read_csv(csv_path)
        self.weights = dict(zip(df.symptom.str.lower(), df.weight))

    def calculate(self, symptoms):
        score = 0

        for s in symptoms:
            s = s.lower()
            for key, weight in self.weights.items():
                if key in s:
                    score += weight
                    break

        if score < 3:
            level = "low"
        elif score < 6:
            level = "medium"
        else:
            level = "high"

        return score, level
