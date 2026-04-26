# Project Setup and Run Instructions

This project consists of three services that need to be run simultaneously in separate terminals.

## Prerequisites

- Python 3.x installed
- Node.js and npm installed
- Virtual environments set up in `agentic` and `backend` directories
- docker compose the database and mqtt

## Running the Services

You'll need to open **three separate terminal windows/tabs** and run each service in its own terminal.

### Terminal 1: Agentic Service
```bash
cd Agentic_workflow
source venv/bin/activate  # On Windows: venv\Scripts\activate
python src/api.py
```

### Terminal 2: Backend Service
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```

### Terminal 3: Frontend Service
```bash
cd frontend
npm run dev
```

### Terminal 4: exapmle dtc code
```bash
$payload = @{
   vin = "XXXXXXXXXXXXXXXXX"
   dtc_list = @("P0211")
   mileage = 98000
   timestamp = "2026-04-06T12:00:00Z"
 } | ConvertTo-Json -Compress
 
 $payload | docker exec -i carbrain-mqtt mosquitto_pub -h localhost -p 1883 -t vehicle/f/dtc -s

```

## Stopping the Services

To stop any service, press `Ctrl+C` in the respective terminal window.

## Troubleshooting

- **Virtual environment not found**: Make sure you've created the virtual environment first with `python -m venv venv`
- **Module not found errors**: Ensure all dependencies are installed with `pip install -r requirements.txt` (for Python services) or `npm install` (for frontend)
- **Port already in use**: Check if another instance is already running and stop it first

## Notes

- All three services must be running for the full application to work properly
- Keep all terminal windows open while using the application
- Check each terminal for error messages if something isn't working
