# Computer Use Tool

## Setup

### Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Load environment variables

Create a `.env` file in the root directory of your project and add your environment variables:

```
HOSTNAME=localhost
ANTHROPIC_API_KEY=<your api key>
```

### Start the server

```bash
uvicorn main:app --reload --env-file .env
```

This command starts the Uvicorn server, reloads it automatically when changes are detected, and reads the environment variables from the `.env` file.

**Note:** This setup requires Docker to be installed and running on your machine.

