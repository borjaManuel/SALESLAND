# Excel to PostgreSQL Importer

Python application for importing data from Microsoft Excel files into a PostgreSQL database.

The project has been designed with a modular architecture, making it easy to maintain, extend and deploy in customer environments.

---

## Features

* Import data from Excel workbooks.
* PostgreSQL database connectivity using SQLAlchemy.
* Environment-based configuration using `.env`.
* Configuration validation before execution.
* Centralized logging with automatic log rotation.
* Dependency management with `uv`.

---

## Project Structure

```text
.
├── logs/
├── src/
│   ├── checks/
│   ├── config/
│   ├── database/
│   ├── logger/
│   ├── services/
│   └── main.py
├── .env.example
├── .python-version
├── pyproject.toml
├── uv.lock
└── README.md
└── docker-compose.yml

```

---

## Requirements

* Python 3.13
* PostgreSQL
* Docker
* Docker Compose
* uv

---

## Installation

Clone the repository:

```bash
git clone https://github.com/borjaManuel/SALESLAND.git
cd SALESLAND
```

Install the project dependencies:

```bash
uv sync
```

---

## PostgreSQL with Docker

The project includes a Docker Compose configuration to run a PostgreSQL
database for development and testing purposes.

Start the PostgreSQL container:

```bash
docker compose up -d
```

Check the container status:
```bash
docker compose ps
```

Stop the PostgreSQL container:
```bash
docker compose down
```
---

## Configuration

Create a `.env` file based on the provided template:

```bash
cp .env.example .env
```

Configure the following variables:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=database
DB_USER=user
DB_PASSWORD=password
```

---

## Configuration Check

Before running the application, verify that the configuration and database connection are valid.

```bash
uv run src/main.py --check
```

---

## Running the Application

```bash
uv run src/main.py
```

---

## Logging

The application writes logs to the `logs/` directory.

Logging configuration:

* Automatic file rotation.
* Maximum log size: **5 MB**.
* Maximum of **5** backup files.
* Console and file output.

---

## Technologies

* Python 3.13
* SQLAlchemy
* PostgreSQL
* python-dotenv
* uv
* Docker
* Docker Compose

---

## License

Internal project.
