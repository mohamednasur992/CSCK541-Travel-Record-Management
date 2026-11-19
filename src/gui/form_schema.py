"""How each record type appears in the page's forms, tables and searches.

The page uses readable field names ("Phone Number", "Client_ID"); the stored
records use the keys from ``record.schema``. This module is the single
place that connects the two and describes every form field.
"""

from record import schema
from record.schema import AIRLINE, CLIENT, FLIGHT

ALL_FIELDS = "All fields"      # search-field choice meaning "match any field"

# City names: letters, spaces, hyphens, apostrophes and full stops, 2 to 60 characters.
CITY_MIN_LENGTH = 2
CITY_MAX_LENGTH = 60

# Page field name -> stored record key, per record type. The page shows the
# brief's field names, which are also the stored keys, so this maps each name
# to itself; it remains the one list of which fields each form has.
FIELD_MAP = {
    CLIENT: {key: key for key in schema.CLIENT_FIELDS if key != schema.TYPE},
    AIRLINE: {key: key for key in schema.AIRLINE_FIELDS if key != schema.TYPE},
    FLIGHT: {key: key for key in schema.FLIGHT_KEY_FIELDS},
}

# Field kinds understood by the page.
INT, STR, DATE = "int", "str", "date"   # DATE = date and time

# (page name, label, kind, required, max length, hint) – in form order.
FIELD_SPECS = {
    CLIENT: (
        ("ID", "Client ID", INT, True, 9, ""),
        ("Name", "Full Name", STR, True, 100, ""),
        ("Address Line 1", "Address Line 1", STR, True, 100, ""),
        ("Address Line 2", "Address Line 2", STR, False, 100, "optional"),
        ("Address Line 3", "Address Line 3", STR, False, 100, "optional"),
        ("City", "City", STR, True, CITY_MAX_LENGTH, ""),
        ("State", "State / Province", STR, False, 100, "optional"),
        ("Zip Code", "Zip / Postal Code", STR, False, 20, "optional"),
        ("Country", "Country", STR, True, 100, "suggested from city"),
        ("Phone Number", "Phone Number", STR, True, 30, "digits, spaces, + - ( )"),
    ),
    AIRLINE: (
        ("ID", "Airline ID", INT, True, 9, ""),
        ("Company Name", "Company Name", STR, True, 100, ""),
    ),
    FLIGHT: (
        ("Client_ID", "Client", INT, True, 9, "must already exist"),
        ("Airline_ID", "Airline", INT, True, 9, "must already exist"),
        ("Date", "Departure Date and Time", DATE, True, 16, schema.DATE_FORMAT_HINT),
        ("Start City", "Start City", STR, True, CITY_MAX_LENGTH, ""),
        ("End City", "End City", STR, True, CITY_MAX_LENGTH, ""),
    ),
}

# Rows of the form, as lists of page field names.
FORM_ROWS = {
    CLIENT: [["ID", "Name"], ["Address Line 1"], ["Address Line 2", "Address Line 3"],
             ["City", "State"], ["Zip Code", "Country"], ["Phone Number"]],
    AIRLINE: [["ID", "Company Name"]],
    FLIGHT: [["Client_ID"], ["Airline_ID"], ["Date"], ["Start City", "End City"]],
}

# Flight fields that must name an existing record of another type.
LINK_FIELDS = {"Client_ID": CLIENT, "Airline_ID": AIRLINE}
