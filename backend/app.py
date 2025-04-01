from fastapi import FastAPI
from .db import weather_test

app = FastAPI()

@app.get("/test/")
async def test():
    test = weather_test.find_one({"name.first": "Alan"})
    print("API call: \n", test)
    
@app.get("/weather/test")
async def weather_test():
    