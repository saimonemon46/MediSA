import pandas as pd

class SymptomExtractor:
    def __init__(self, symptom_csv="data/symptoms.csv"):
        self.symptoms = set(pd.read_csv(symptom_csv)["symptom"].str.lower())

    def extract(self, text: str):
        text = text.lower()
        return [s for s in self.symptoms if s in text]
