# CarSharing Client-Server Demo

## Backend (FastAPI)
```
cd backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

## Car Simulator (Telematics)
```
cd car-simulator
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python car_simulator.py   # enter VIN (e.g., VIN0001)
```
Run multiple terminals with different VINs to simulate several cars at once.

## Frontend (React + Vite + TypeScript)
```
cd frontend
npm install
npm run dev
```
Open the displayed local URL; UI is centered and mobile-like.

## Demo Scenario
1. Open frontend, fill login fields (location near 47.16 / 27.59) and connect (REGISTER_CLIENT).
2. Click "Query Available Cars" (QUERY_CARS_RESULT lists seeded cars sorted by distance).
3. Select a car and click "Start Rental" (START_RENTAL_OK). Simulator unlocks car.
4. Click "End Rental" while simulator has doors open/lights on/engine on to force denial (END_RENTAL_ERROR with recommended action).
5. In simulator CLI, toggle doors/lights/engine to closed/off.
6. Click "End Rental" again; backend queries state, locks car, finalizes rental (END_RENTAL_OK).

## Notes
- WebSocket endpoint: `ws://localhost:8000/ws`
- Data is in-memory only; cars are pre-seeded near 47.16 / 27.59.
