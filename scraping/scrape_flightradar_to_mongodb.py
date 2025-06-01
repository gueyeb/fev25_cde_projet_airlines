import time

from bs4 import BeautifulSoup
from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver


def extract_flight_history(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find("table", {"id": "tbl-datatable"})
    rows = table.find("tbody").find_all("tr", class_="data-row")

    flights = []
    for row in rows:
        cols = row.find_all("td")
        try:
            flights.append({
                "date": cols[2].text.strip(),
                "from": cols[3].text.strip().split("(")[-1].strip(")"),
                "to": cols[4].text.strip().split("(")[-1].strip(")"),
                "aircraft": cols[5].text.strip(),
                "flight_time": cols[6].text.strip(),
                "std": cols[7].text.strip(),
                "atd": cols[8].text.strip(),
                "sta": cols[9].text.strip(),
                "status": cols[11].text.strip()
            })
        except Exception as e:
            print(f"Erreur parsing ligne: {e}")
    return flights


def save_to_mongodb(data, flight_number):
    client = MongoClient("mongodb://localhost:27018")
    db = client["dst_airlines"]
    collection = db["flightradar_history"]

    # Ajout d’un champ identifiant de vol
    for flight in data:
        flight["flight_number"] = flight_number.upper()

    result = collection.insert_many(data)
    print(f"{len(result.inserted_ids)} vols insérés dans MongoDB pour {flight_number}")


def scrape_flightradar24(flight_number):
    url = f"https://www.flightradar24.com/data/flights/{flight_number.lower()}"
    driver = init_driver()
    print(f"Chargement de la page {url}")
    driver.get(url)
    time.sleep(8)  # attendre que les données soient bien chargées

    html = driver.page_source
    driver.quit()

    flights = extract_flight_history(html)
    if flights:
        save_to_mongodb(flights, flight_number)
    else:
        print("Aucun vol trouvé ou structure HTML modifiée.")


if __name__ == "__main__":
    scrape_flightradar24("LH456")  # ✈️ Remplace par le vol de ton choix
