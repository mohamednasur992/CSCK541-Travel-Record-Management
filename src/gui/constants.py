"""Shared reference data for the Travel Record Management System."""


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


# Default nationality suggestions based on the selected city.
#
# These values provide a convenient starting point only. The nationality
# field remains editable because a client's city does not necessarily
# determine the client's nationality.
CITY_TO_NATIONALITY = {
    # Africa
    "Accra": "Ghanaian",
    "Cairo": "Egyptian",
    "Cape Town": "South African",
    "Casablanca": "Moroccan",
    "Gaborone": "Motswana",
    "Johannesburg": "South African",
    "Lagos": "Nigerian",
    "Nairobi": "Kenyan",
    "Pretoria": "South African",

    # Asia
    "Bangkok": "Thai",
    "Beijing": "Chinese",
    "Delhi": "Indian",
    "Hong Kong": "Hong Konger",
    "Jakarta": "Indonesian",
    "Kuala Lumpur": "Malaysian",
    "Manila": "Filipino",
    "Mumbai": "Indian",
    "Seoul": "South Korean",
    "Shanghai": "Chinese",
    "Singapore": "Singaporean",
    "Tokyo": "Japanese",

    # Middle East
    "Abu Dhabi": "Emirati",
    "Doha": "Qatari",
    "Dubai": "Emirati",
    "Istanbul": "Turkish",
    "Jeddah": "Saudi Arabian",
    "Riyadh": "Saudi Arabian",

    # Europe
    "Amsterdam": "Dutch",
    "Barcelona": "Spanish",
    "Berlin": "German",
    "Dublin": "Irish",
    "Frankfurt": "German",
    "Lisbon": "Portuguese",
    "London": "British",
    "Madrid": "Spanish",
    "Paris": "French",
    "Rome": "Italian",
    "Vienna": "Austrian",
    "Zurich": "Swiss",

    # North America
    "Chicago": "American",
    "Los Angeles": "American",
    "Mexico City": "Mexican",
    "New York": "American",
    "Toronto": "Canadian",
    "Vancouver": "Canadian",

    # South America
    "Bogota": "Colombian",
    "Buenos Aires": "Argentinian",
    "Sao Paulo": "Brazilian",

    # Oceania
    "Auckland": "New Zealander",
    "Sydney": "Australian",
}