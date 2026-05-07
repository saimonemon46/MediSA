import pandas as pd

class DiseaseSpecialistMapper:
    def __init__(self, csv_path=r"D:\ALL Projects\medical_agent\data\Disease_Specialist.csv"):
        df = pd.read_csv(csv_path)

        # normalize
        df["Disease_norm"] = df["Disease"].str.lower().str.strip()
        df["Specialist_norm"] = df["Specialist"].str.lower().str.strip()

        self.mapping = dict(
            zip(df["Disease_norm"], df["Specialist_norm"])
        )

    def infer_specialist(self, symptoms):
        """
        Infer specialist from symptom keywords.
        This is NOT diagnosis.
        """
        text = " ".join(symptoms).lower()

        # ---- skin ----
        if any(k in text for k in ["rash", "itch", "skin", "red", "spot"]):
            return "dermatologist"

        # ---- heart ----
        if any(k in text for k in ["chest pain", "chest", "heart", "tightness"]):
            return "cardiologist"

        # ---- stomach ----
        if any(k in text for k in ["acid", "vomit", "stomach", "abdominal"]):
            return "gastroenterologist"

        # ---- breathing ----
        if any(k in text for k in ["breath", "asthma", "wheezing"]):
            return "pulmonologist"

        # ---- neuro ----
        if any(k in text for k in ["headache", "migraine", "vertigo", "dizzy"]):
            return "neurologist"

        # fallback
        return "medicine"
