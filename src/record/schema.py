"""Names used in stored records: record types, field keys and the date format.

The JSON Lines file uses exactly these keys, so they are defined once here
and imported wherever a record is built or read.
"""

# Record types (the value of every record's "type" field)
CLIENT = "Client"
AIRLINE = "Airline"
FLIGHT = "Flight"
RECORD_TYPES = (CLIENT, AIRLINE, FLIGHT)

# Field names exactly as the assignment brief gives them; they are the keys
# stored in the JSON Lines file.

# Keys shared by several record types
TYPE = "Type"
ID = "ID"

# Client keys
NAME = "Name"
ADDRESS_LINE_1 = "Address Line 1"
ADDRESS_LINE_2 = "Address Line 2"
ADDRESS_LINE_3 = "Address Line 3"
CITY = "City"
STATE = "State"
ZIP_CODE = "Zip Code"
COUNTRY = "Country"
PHONE_NUMBER = "Phone Number"
CLIENT_FIELDS = (ID, TYPE, NAME, ADDRESS_LINE_1, ADDRESS_LINE_2, ADDRESS_LINE_3,
                 CITY, STATE, ZIP_CODE, COUNTRY, PHONE_NUMBER)

# Airline keys
COMPANY_NAME = "Company Name"
AIRLINE_FIELDS = (ID, TYPE, COMPANY_NAME)

# Flight keys (a flight has no ID; these five values identify it)
CLIENT_ID = "Client_ID"
AIRLINE_ID = "Airline_ID"
DATE = "Date"
START_CITY = "Start City"
END_CITY = "End City"
FLIGHT_KEY_FIELDS = (CLIENT_ID, AIRLINE_ID, DATE, START_CITY, END_CITY)
FLIGHT_FIELDS = (TYPE,) + FLIGHT_KEY_FIELDS

# Which flight key refers to which record type
LINK_KEY = {CLIENT: CLIENT_ID, AIRLINE: AIRLINE_ID}

DATE_FORMAT = "%Y-%m-%d %H:%M"    # flight date/time, stored as "YYYY-MM-DD HH:MM" text
DATE_FORMAT_HINT = "YYYY-MM-DD HH:MM"
DAY_LENGTH = len("YYYY-MM-DD")      # the calendar-day part of a stored date/time


# Keys used by the earlier version of the program (before the brief's names
# were adopted), mapped to the current keys. Old fields the brief does not
# have (email, passport number, nationality, emergency contact) are dropped.
LEGACY_KEYS = {
    "id": ID, "type": TYPE, "name": NAME, "address": ADDRESS_LINE_1, "city": CITY,
    "phone_number": PHONE_NUMBER, "company_name": COMPANY_NAME, "client_id": CLIENT_ID,
    "airline_id": AIRLINE_ID, "date": DATE, "start_city": START_CITY, "end_city": END_CITY,
}
LEGACY_DEFAULT_TIME = "00:00"   # old flights stored a date only
