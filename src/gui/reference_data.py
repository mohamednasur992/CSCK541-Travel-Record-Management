"""Reference data offered as suggestions in the forms (airlines, cities, countries).

The lists are suggestions only: every form field also accepts free text.
"""


# Major international and regional airlines covering Africa, Asia,
# Europe, the Middle East, North America, South America, and Oceania.
# Two-character codes in brackets are IATA airline designators.
WORLD_AIRLINES = (
    # Africa
    "Air Mauritius (MK)",
    "Airlink (4Z)",
    "EgyptAir (MS)",
    "Ethiopian Airlines (ET)",
    "FlySafair (FA)",
    "Kenya Airways (KQ)",
    "South African Airways (SA)",

    # Asia
    "Air China (CA)",
    "Air India (AI)",
    "All Nippon Airways - ANA (NH)",
    "Asiana Airlines (OZ)",
    "Cathay Pacific (CX)",
    "China Airlines (CI)",
    "China Eastern Airlines (MU)",
    "China Southern Airlines (CZ)",
    "EVA Air (BR)",
    "Garuda Indonesia (GA)",
    "Hainan Airlines (HU)",
    "IndiGo (6E)",
    "Japan Airlines (JL)",
    "Korean Air (KE)",
    "Malaysia Airlines (MH)",
    "Singapore Airlines (SQ)",
    "Thai Airways International (TG)",
    "Vietnam Airlines (VN)",

    # Middle East
    "Emirates (EK)",
    "Etihad Airways (EY)",
    "Qatar Airways (QR)",
    "Saudia (SV)",

    # Europe
    "Air France (AF)",
    "Austrian Airlines (OS)",
    "British Airways (BA)",
    "Finnair (AY)",
    "Iberia (IB)",
    "ITA Airways (AZ)",
    "KLM Royal Dutch Airlines (KL)",
    "LOT Polish Airlines (LO)",
    "Lufthansa (LH)",
    "SAS Scandinavian Airlines (SK)",
    "Swiss International Air Lines (LX)",
    "Turkish Airlines (TK)",
    "Virgin Atlantic (VS)",

    # North America
    "Air Canada (AC)",
    "Alaska Airlines (AS)",
    "American Airlines (AA)",
    "Delta Air Lines (DL)",
    "JetBlue (B6)",
    "United Airlines (UA)",

    # South America
    "Avianca (AV)",
    "LATAM Airlines (LA)",

    # Oceania
    "Qantas (QF)",
)


# Major cities representing the main geographic regions supported
# by the travel-management application.
WORLD_CITIES = (
    # Africa
    "Accra",
    "Cairo",
    "Cape Town",
    "Casablanca",
    "Gaborone",
    "Johannesburg",
    "Lagos",
    "Nairobi",
    "Pretoria",

    # Asia
    "Bangkok",
    "Beijing",
    "Delhi",
    "Hong Kong",
    "Jakarta",
    "Kuala Lumpur",
    "Manila",
    "Mumbai",
    "Seoul",
    "Shanghai",
    "Singapore",
    "Tokyo",

    # Middle East
    "Abu Dhabi",
    "Doha",
    "Dubai",
    "Istanbul",
    "Jeddah",
    "Riyadh",

    # Europe
    "Amsterdam",
    "Barcelona",
    "Berlin",
    "Dublin",
    "Frankfurt",
    "Lisbon",
    "London",
    "Madrid",
    "Paris",
    "Rome",
    "Vienna",
    "Zurich",

    # North America
    "Chicago",
    "Los Angeles",
    "Mexico City",
    "New York",
    "Toronto",
    "Vancouver",

    # South America
    "Bogota",
    "Buenos Aires",
    "Sao Paulo",

    # Oceania
    "Auckland",
    "Sydney",
)


# Country suggested when the user types a client's city. The suggestion
# only fills an empty Country field; the user can always change it.
CITY_TO_COUNTRY = {
    # Africa
    "Accra": "Ghana",
    "Cairo": "Egypt",
    "Cape Town": "South Africa",
    "Casablanca": "Morocco",
    "Gaborone": "Botswana",
    "Johannesburg": "South Africa",
    "Lagos": "Nigeria",
    "Nairobi": "Kenya",
    "Pretoria": "South Africa",

    # Asia
    "Bangkok": "Thailand",
    "Beijing": "China",
    "Delhi": "India",
    "Hong Kong": "Hong Kong",
    "Jakarta": "Indonesia",
    "Kuala Lumpur": "Malaysia",
    "Manila": "Philippines",
    "Mumbai": "India",
    "Seoul": "South Korea",
    "Shanghai": "China",
    "Singapore": "Singapore",
    "Tokyo": "Japan",

    # Middle East
    "Abu Dhabi": "United Arab Emirates",
    "Doha": "Qatar",
    "Dubai": "United Arab Emirates",
    "Istanbul": "Turkey",
    "Jeddah": "Saudi Arabia",
    "Riyadh": "Saudi Arabia",

    # Europe
    "Amsterdam": "Netherlands",
    "Barcelona": "Spain",
    "Berlin": "Germany",
    "Dublin": "Ireland",
    "Frankfurt": "Germany",
    "Lisbon": "Portugal",
    "London": "United Kingdom",
    "Madrid": "Spain",
    "Paris": "France",
    "Rome": "Italy",
    "Vienna": "Austria",
    "Zurich": "Switzerland",

    # North America
    "Chicago": "United States",
    "Los Angeles": "United States",
    "Mexico City": "Mexico",
    "New York": "United States",
    "Toronto": "Canada",
    "Vancouver": "Canada",

    # South America
    "Bogota": "Colombia",
    "Buenos Aires": "Argentina",
    "Sao Paulo": "Brazil",

    # Oceania
    "Auckland": "New Zealand",
    "Sydney": "Australia",
}
