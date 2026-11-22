"""Shared constants for the UrbanPulse portal (public and authority sides)."""

COORDS = {"Hampankatta": (12.8696, 74.8433), "Kankanady": (12.8791, 74.8500),
          "Surathkal": (13.0108, 74.7942), "Lalbagh": (12.8860, 74.8420),
          "Bejai": (12.8950, 74.8420), "Kadri": (12.8870, 74.8530),
          "Pumpwell": (12.8630, 74.8630), "Jyothi": (12.8730, 74.8400)}

# category: (department, head, phone, email). DEMO DATA ONLY: replace with the real contacts.
DEPTS = {"Road": ("Roads and Public Works", "A. Rao", "0000-000001", "roads@demo.example"),
         "Drainage": ("Drainage and Sewerage", "S. Shetty", "0000-000002", "drainage@demo.example"),
         "Water": ("Water Supply Board", "M. D'Souza", "0000-000003", "water@demo.example"),
         "Garbage": ("Solid Waste Management", "K. Naik", "0000-000004", "waste@demo.example"),
         "Transport": ("Transport Department", "R. Bhat", "0000-000005", "transport@demo.example"),
         "Other": ("General Grievance Cell", "P. Kamath", "0000-000006", "general@demo.example")}

# "Pending approval" = the department says it is solved and the main admin has not approved yet.
# Citizens never see that status: they keep seeing "In progress" until the admin approves.
STATUSES = ["New", "In progress", "Pending approval", "Resolved", "Rejected"]
OPEN_STATUSES = ["New", "In progress"]
SCORE = {"Angry": -2, "Frustrated": -1, "Neutral": 0, "Satisfied": 1, "Happy": 2}

# National emergency numbers in India (these are real).
EMERGENCY = [("112", "Any emergency"), ("100", "Police"), ("101", "Fire"), ("108", "Ambulance")]
