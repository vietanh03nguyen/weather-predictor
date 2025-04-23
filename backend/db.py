from pymongo import MongoClient
from pymongo.server_api import ServerApi

MONGO_URL = 'mongodb+srv://vietanh03nguyen:vietanh03nguyen@cluster0.olurtc6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'

# Create a new client and connect to the server
client = MongoClient(MONGO_URL, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
    
    
db = client['weather_db']
col = db['realtime_weather']




