# Project Setup and Run Instructions

This project requires simultaneous execution of multiple services.

## Prerequisites

- Linux OS with `vcan` support
- Docker installed
- `.env` file setup correctly for the project to function

## Running the Services with Docker Compose

Before running the compose file, you must execute the virtual CAN setup script:

```bash
./IoT/setupcan0.sh
```

Then, you can start the services using the Compose file:

```sh
source .env
docker compose up
```

## Production Deployment

A production Compose file is provided which uses pre-built DockerHub images. To deploy:

```sh
source .env
./IoT/setupcan0.sh
docker compose -f docker-compose.prod.yml up -d
```

## Local Development Requirements

If you wish to develop individual modules locally, you'll need the following package managers:

- **uv**: Required for `backend`, `Agentic_Workflow`, and `IoT/car_simulator`
- **pnpm**: Required for `frontend`
- **ESP-IDF**: Required for `IoT/Mechanic`

## Stopping the Services

To stop the services, use `docker compose down` (add `-f docker-compose.prod.yml` if running production) or press `Ctrl+C` in the terminal if running in the foreground.

## Troubleshooting

- **Virtual environment not found**: Make sure you've created the virtual environment first using `uv`
- **Module not found errors**: Ensure all dependencies are installed with `uv` (for Python services) or `pnpm install` (for frontend)
- **Port already in use**: Check if another instance is already running and stop it first

## Notes

- All services must be running for the full application to work properly.
- Keep the terminal windows open or run services in detached mode (`-d`).
- Check your container logs if something isn't working as expected.
