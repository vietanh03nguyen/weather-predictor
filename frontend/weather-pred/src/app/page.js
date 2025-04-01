import Image from "next/image";
import { fetchWeatherData } from "../../utils/fetchData";


export default function Home() {
  return (
    fetchWeatherData()
  );
}
