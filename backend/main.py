from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from datetime import datetime

app = FastAPI(
    title="CloudAuto Diagnostics AI - API",
    description="System diagnostyczno-doradczy dla marek Mercedes-Benz, BMW, Audi",
    version="1.0.0"
)

# Odblokowanie komunikacji dla przyszłego Front-endu (React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "cloudauto.db"

# --- INICJALIZACJA BAZY DANYCH ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela pojazdów
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            year INTEGER NOT NULL,
            vin TEXT UNIQUE NOT NULL,
            owner_name TEXT NOT NULL
        )
    """)
    
    # Tabela diagnoz i historii napraw
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnostics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            dtc_codes TEXT NOT NULL,
            ai_diagnosis TEXT NOT NULL,
            repair_steps TEXT NOT NULL,
            parts_to_check TEXT NOT NULL,
            status TEXT DEFAULT 'W toku',
            created_at TEXT NOT NULL,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- MODELE DANYCH (Schematy wejściowe) ---
class VehicleCreate(BaseModel):
    brand: str  # Mercedes-Benz, BMW, Audi
    model: str
    year: int
    vin: str
    owner_name: str

class DiagnosticScanRequest(BaseModel):
    vehicle_id: int
    dtc_codes: List[str]  # np. ["P0300", "P0171"]

class StatusUpdateRequest(BaseModel):
    status: str  # np. "W toku", "Oczekiwanie na części", "Zakończone"

# --- MODUŁ DORADCZY (Logika inspirowana TIPS / Xentry / ISTA) ---
def analyze_faults(brand: str, codes: List[str]):
    codes_set = set(code.upper().strip() for code in codes)
    
    # 1. Inteligentna diagnoza skojarzona (Korelacja błędów!)
    if "P0300" in codes_set and "P0171" in codes_set:
        if brand == "Mercedes-Benz":
            return {
                "diagnosis": "KORELACJA BŁĘDÓW (Biuletyn MB): Jednoczesne wypadanie zapłonów (P0300) oraz uboga mieszanka (P0171) wskazują na nieszczelność układu odpowietrzania skrzyni korbowej (odmy) lub pęknięty przewód podciśnienia, a nie usterkę cewek zapłonowych.",
                "steps": "1. Wykonaj test dymowy układu dolotowego.\n2. Sprawdź zawór odpowietrzania skrzyni korbowej pod kolektorem ssącym.\n3. Zweryfikuj korekty krótkoterminowe i długoterminowe paliwa (STFT/LTFT) na biegu jałowym.",
                "parts": "Zawór odmy (częściowy ładunek), przewód odpowietrzający, uszczelki kolektora ssącego."
            }
        elif brand == "BMW":
            return {
                "diagnosis": "KORELACJA BŁĘDÓW (Biuletyn BMW): Zestawienie P0300 i P0171 typowe dla uszkodzonej membrany zaworu regulacji ciśnienia w pokrywie zaworów (PCV) lub nieszczelności za przepływomierzem MAF.",
                "steps": "1. Sprawdź podciśnienie pod korkiem wlewu oleju na pracującym silniku.\n2. Skontroluj rurę dolotową pod kątem pęknięć na harmonijkach.\n3. Po wymianie zresetuj adaptacje mieszanki paliwowo-powietrznej.",
                "parts": "Pokrywa zaworów / membrana PCV, rura dolotowa przed przepustnicą."
            }
        elif brand == "Audi":
            return {
                "diagnosis": "KORELACJA BŁĘDÓW (Biuletyn Audi/VAG): Błędy P0300 + P0171 w silnikach TFSI/TSI silnie wskazują na uszkodzenie separatora oleju (odmy) lub nieszczelność tylnego uszczelniacza wału korbowego.",
                "steps": "1. Odłącz przewód od separatora oleju i sprawdź zmianę pracy silnika.\n2. Sprawdź okolicę połączenia silnika ze skrzynią biegów pod kątem zapoceń olejowych (zasysanie lewego powietrza).",
                "parts": "Separator oleju (Odma VAG), tylny uszczelniacz wału korbowego, zawór N80."
            }

    # 2. Pojedyncze specyficzne kody błędów
    if "P0299" in codes_set:
        return {
            "diagnosis": f"Zbyt niskie ciśnienie doładowania turbosprężarki dla pojazdu marki {brand} (Kod P0299).",
            "steps": "1. Sprawdź szczelność układu intercoolera oraz przewodów ciśnieniowych.\n2. Zweryfikuj pracę nastawnika turbosprężarki / zaworu Wastegate (test elementów wykonawczych).\n3. Sprawdź drożność filtra DPF/katalizatora (zbyt wysokie ciśnienie wsteczne).",
            "parts": "Nastawnik turbosprężarki, przetwornik ciśnienia, przewód intercoolera."
        }
        
    if "U0100" in codes_set:
        return {
            "diagnosis": f"Utrata komunikacji ze sterownikiem silnika ECM/PCM na magistrali CAN ({brand}).",
            "steps": "1. Zmierz rezystancję magistrali CAN-High / CAN-Low (prawidłowa wartość: 60 Ohm).\n2. Sprawdź przekaźnik główny zasilania sterownika silnika w skrzynce bezpieczników.\n3. Zweryfikuj piny złącza ECU pod kątem wilgoci lub korozji.",
            "parts": "Przekaźnik zasilania ECU, wiązka magistrali CAN, złącze sterownika."
        }

    # 3. Domyślna odpowiedź analityczna dla innych kodów
    codes_str = ", ".join(codes_set)
    return {
        "diagnosis": f"Wykryto błędy sterownika ({codes_str}) w pojeździe {brand}. Wymagana weryfikacja parametrów rzeczywistych (Live Data).",
        "steps": "1. Odczytaj ramki zamrożone (Freeze Frame) dla momentu wystąpienia błędu (przebieg, temp. płynu, obroty).\n2. Sprawdź napięcie zasilania czujników (5V / 12V) powiązanych z kodem.\n3. Wykasuj kody i wykonaj jazdę próbną, monitorując parametry na żywo.",
        "parts": "Wiązka elektryczna, złącza czujników, odpowiedni moduł wykonawczy zgodny z kodem DTC."
    }

# --- ENDPOINTY API (Zgodne z Etapem 1) ---

@app.get("/api/vehicles")
def get_vehicles():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicles ORDER BY id DESC")
    vehicles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return vehicles

@app.post("/api/vehicles")
def create_vehicle(vehicle: VehicleCreate):
    allowed_brands = ["Mercedes-Benz", "BMW", "Audi"]
    if vehicle.brand not in allowed_brands:
        raise HTTPException(
            status_code=400, 
            detail=f"Ograniczenie systemu: Obsługiwane są wyłącznie marki: {', '.join(allowed_brands)}"
        )
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO vehicles (brand, model, year, vin, owner_name) VALUES (?, ?, ?, ?, ?)",
            (vehicle.brand, vehicle.model, vehicle.year, vehicle.vin.upper().strip(), vehicle.owner_name)
        )
        conn.commit()
        vehicle_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Pojazd o podanym numerze VIN już istnieje w bazie.")
    
    conn.close()
    return {"message": "Pojazd dodany pomyślnie", "vehicle_id": vehicle_id}

@app.post("/api/diagnostics/scan")
def run_diagnostic_scan(scan: DiagnosticScanRequest):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM vehicles WHERE id = ?", (scan.vehicle_id,))
    vehicle = cursor.fetchone()
    if not vehicle:
        conn.close()
        raise HTTPException(status_code=404, detail="Nie znaleziono pojazdu o podanym ID.")
    
    # Uruchomienie modułu doradczego
    result = analyze_faults(vehicle["brand"], scan.dtc_codes)
    codes_formatted = ", ".join([c.upper().strip() for c in scan.dtc_codes])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cursor.execute("""
        INSERT INTO diagnostics (vehicle_id, dtc_codes, ai_diagnosis, repair_steps, parts_to_check, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'W toku', ?)
    """, (scan.vehicle_id, codes_formatted, result["diagnosis"], result["steps"], result["parts"], now))
    
    conn.commit()
    diag_id = cursor.lastrowid
    conn.close()
    
    return {
        "diagnostic_id": diag_id,
        "vehicle": f"{vehicle['brand']} {vehicle['model']} ({vehicle['vin']})",
        "dtc_codes": codes_formatted,
        "analysis": result,
        "status": "W toku",
        "created_at": now
    }

@app.get("/api/diagnostics/{vehicle_id}")
def get_vehicle_diagnostics(vehicle_id: int):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diagnostics WHERE vehicle_id = ? ORDER BY id DESC", (vehicle_id,))
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return history

@app.patch("/api/diagnostics/{diagnostic_id}/status")
def update_repair_status(diagnostic_id: int, update: StatusUpdateRequest):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE diagnostics SET status = ? WHERE id = ?", (update.status, diagnostic_id))
    conn.commit()
    conn.close()
    return {"message": "Status zaktualizowany", "new_status": update.status}

@app.get("/api/client/report/{vin}")
def get_client_report(vin: str):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM vehicles WHERE vin = ?", (vin.upper().strip(),))
    vehicle = cursor.fetchone()
    if not vehicle:
        conn.close()
        raise HTTPException(status_code=404, detail="Nie znaleziono pojazdu o podanym numerze VIN.")
        
    cursor.execute("SELECT dtc_codes, ai_diagnosis, repair_steps, parts_to_check, status, created_at FROM diagnostics WHERE vehicle_id = ? ORDER BY id DESC", (vehicle["id"],))
    diagnostics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        "vehicle_info": dict(vehicle),
        "repair_history": diagnostics,
        "access_mode": "READ_ONLY (Widok Klienta)"
    }
