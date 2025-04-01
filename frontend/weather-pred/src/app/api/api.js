import axios from "axios";

const apiURL = "http://localhost:8000"
const axiosInstance = axios.create({
    baseURL: apiURL
})

export default axiosInstance