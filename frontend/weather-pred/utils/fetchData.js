import axios from "axios";
import axiosInstance from "@/app/api/api";

export async function fetchWeatherData() {
    try{
        const response = await axiosInstance.get("/test/")
        return response.data
    }catch(error){
        console.error("Error fetching weather data: ", error)
    }
}