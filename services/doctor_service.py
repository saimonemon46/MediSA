import pandas as pd

class DoctorService:
    def __init__(self, csv_path="data/doctors.csv"):
        self.df = pd.read_csv(csv_path)

        # -------------------------
        # Normalize location
        # -------------------------
        self.df["Location_norm"] = (
            self.df["Location"]
            .astype(str)
            .str.lower()
            .str.replace(r"[^a-z\s]", " ", regex=True)
            .str.strip()
        )

        # -------------------------
        # Normalize speciality
        # -------------------------
        self.df["Speciality_norm"] = (
            self.df["Speciality"]
            .astype(str)
            .str.lower()
            .str.strip()
        )

    def find(self, location: str, specialty: str | None = None, limit: int = 3):
        """
        Find doctors by location and (optional) specialty.
        """

        if not location:
            return self.df.head(0)

        location = location.lower().strip()

        # -------------------------
        # Location filter
        # -------------------------
        results = self.df[
            self.df["Location_norm"].str.contains(location, na=False)
        ]

        if results.empty:
            return results

        # -------------------------
        # Specialty filter (optional)
        # -------------------------
        if specialty:
            specialty = specialty.lower().strip()

            filtered = results[
                results["Speciality_norm"].str.contains(specialty, na=False)
            ]

            # If no exact specialty match, FALL BACK to Medicine
            if filtered.empty:
                filtered = results[
                    results["Speciality_norm"].str.contains("medicine", na=False)
                ]

            results = filtered if not filtered.empty else results

        # -------------------------
        # Sort by experience
        # -------------------------
        results = results.sort_values(
            by="Experience",
            ascending=False,
            na_position="last"
        )

        return results.head(limit)
