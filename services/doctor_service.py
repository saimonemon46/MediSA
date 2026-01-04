import pandas as pd

class DoctorService:
    def __init__(self, csv_path="data/doctors.csv"):
        self.df = pd.read_csv(csv_path)

        # Normalize location for matching
        self.df["Location_norm"] = (
            self.df["Location"]
            .str.lower()
            .str.replace(r"[^a-z\s]", " ", regex=True)
        )

    def find(self, location, limit=3):
        location = location.lower()

        results = self.df[
            self.df["Location_norm"].str.contains(location, na=False)
        ]

        if results.empty:
            return results

        # Sort by experience (highest first)
        results = results.sort_values(by="Experience", ascending=False)

        # Return at most `limit` doctors
        return results.head(limit)
