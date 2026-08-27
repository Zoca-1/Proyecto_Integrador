import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv


# CONFIGURACIÓN DE LOGS 

# Guarda la salida en 'log_parte_b.txt' y la muestra simultáneamente en consola
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("log_parte_b.txt", mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Cargar variables de entorno desde el archivo .env
load_dotenv()
API_TOKEN = os.getenv("LICHESS_API_TOKEN")

# Flag de simulación: True para validar sin crear torneos reales en Lichess
DRY_RUN = True

# Lista de torneos programados
SCHEDULED_TOURNAMENTS = [
    {
        "name": "Monday Blitz Battle",
        "clockTime": 3,
        "clockIncrement": 2,
        "minutes": 60,
        "startDate": 1788199200000,
        "variant": "standard",
        "rated": "true",
        "description": "Weekly blitz arena open to all ratings."
    },
    {
        "name": "Wednesday Rapid Rumble",
        "clockTime": 10,
        "clockIncrement": 5,
        "minutes": 90,
        "startDate": 1787772600000,
        "variant": "standard",
        "rated": "true",
        "description": "Weekly rapid arena, casual and competitive players welcome."
    },
    {
        "name": "Friday Bullet Frenzy",
        "clockTime": 1,
        "clockIncrement": 0,
        "minutes": 45,
        "startDate": 1787947200000,
        "variant": "standard",
        "rated": "true",
        "description": "Fast-paced bullet arena to close the week."
    },
    {
        "name": "Sunday Classical Clash",
        "clockTime": 30,
        "clockIncrement": 20,
        "minutes": 120,
        "startDate": 1788102000000,
        "variant": "standard",
        "rated": "true",
        "description": "Slow-paced classical arena for deep thinkers."
    }
]

def create_tournament(tournament_data):
    """Crea un torneo en Lichess vía API o simula la petición en modo DRY_RUN."""
    url = "https://lichess.org/api/tournament"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "User-Agent": "LichessAutomationApp/1.0"
    }

    if DRY_RUN:
        logging.info(f"[DRY RUN] Would create tournament: {tournament_data}")
        return True

    try:
        response = requests.post(url, headers=headers, data=tournament_data)
        if response.status_code in [200, 201]:
            logging.info(f"Tournament '{tournament_data['name']}' created successfully!")
            return True
        else:
            logging.error(f"Failed to create tournament. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error connecting to Lichess API: {e}")
        return False

def main():
    logging.info(f"Processing {len(SCHEDULED_TOURNAMENTS)} scheduled tournaments (DRY_RUN={DRY_RUN})...")
    
    for tournament in SCHEDULED_TOURNAMENTS:
        create_tournament(tournament)

if __name__ == "__main__":
    main()
