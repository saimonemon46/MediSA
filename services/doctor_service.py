import pandas as pd

class DoctorService:
    def __init__(self, csv_path="data/doctors.csv"):
        self.df = pd.read_csv(csv_path)

    def find(self, location, keyword):
        return self.df[
            self.df["Location"].str.contains(location, case=False) &
            self.df["Concentration"].str.contains(keyword, case=False)
        ][["Doctor Name", "Speciality", "Experience", "Chamber"]]
