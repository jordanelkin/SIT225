import json
import firebase_admin
from datetime import datetime
fp = open('cert.json','r')
cert = json.load(fp)

databaseURL = 'https://week5-6b340-default-rtdb.asia-southeast1.firebasedatabase.app/'
cred = firebase_admin.credentials.Certificate("cert.json")
default_app = firebase_admin.initialize_app(cred,{'databaseURL':databaseURL})
from firebase_admin import db

# A reference point is always needed to be set
# before any operation is carried out on a database.
#
ref = db.reference("/")

# JSON format data (key/value pair)
data = {  # Outer {} contains inner data structure
	"DHT22":
	{
		"Name":"DHT22",
		"Temperature": 0.0,
		"Relative Humidity": 0.0,
		"Time_Stamp": 0.0
	}

}

