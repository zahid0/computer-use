import os
import pickle
import threading

import requests
from docker import DockerClient
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader

debug = os.getenv("DEBUG") == "true"
app = FastAPI(debug=debug)
client = DockerClient(base_url="unix://var/run/docker.sock")
nginx_config_dir = "nginx"
if not os.path.exists(nginx_config_dir):
    os.makedirs(nginx_config_dir)


@app.get("/")
async def home():
    return FileResponse("index.html")


@app.post("/api/run_container")
async def run_container(request: Request):
    user_token = request.headers.get("Authorization")

    # TODO: Implement logic to validate token and fetch user information.
    if not validate_token(user_token):
        return JSONResponse({"error": "User unauthorized"}, status_code=401)

    image = "ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest"
    containers = client.containers.list()
    ports_6080_in_use = set()
    ports_8501_in_use = set()

    for container in containers:
        # fetch container information
        container_ports = container.attrs["NetworkSettings"]["Ports"]
        print(container_ports)
        if "6080/tcp" in container_ports:
            ports_6080_in_use.add(int(container_ports["6080/tcp"][0]["HostPort"]))
        if "8501/tcp" in container_ports:
            ports_8501_in_use.add(int(container_ports["8501/tcp"][0]["HostPort"]))

    port_8501 = 8501
    while port_8501 in ports_8501_in_use:
        port_8501 += 1
    ports_8501_in_use.add(port_8501)
    port_6080 = 6080
    while port_6080 in ports_6080_in_use or port_6080 in ports_8501_in_use:
        port_6080 += 1
    ports = {"6080": str(port_6080), "8501": str(port_8501)}
    container_name = port_8501
    environment = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "STREAMLIT_SERVER_BASE_URL_PATH": f"/{container_name}",
    }

    kwargs = {
        "ports": ports,
        "environment": environment,
        "name": container_name,
    }
    if os.environ.get("DOCKER_NETWORK"):
        kwargs["network"] = os.environ.get("DOCKER_NETWORK")
    container = client.containers.run(
        image,
        detach=True,
        **kwargs,
    )
    routing_data = {
        "upstream": container.name if os.getenv("NGINX_IN_CONTAINER") else "localhost",
        "locations": [
            {"path": f"{container.name}-screen", "port": port_6080},
            {"path": f"{container.name}-chat", "port": port_8501},
        ],
    }
    app_upstream = (
        os.getenv("APP_UPSTREAM") if os.getenv("APP_UPSTREAM") else "localhost"
    )
    template_env = Environment(loader=FileSystemLoader("."))
    template = template_env.get_template("nginx_template.j2")

    file_path = "routing_data.pkl"
    lock = threading.Lock()
    with lock:
        try:
            with open(file_path, "rb") as file:
                data = pickle.load(file)
        except (FileNotFoundError, EOFError):
            data = []
        data.append(routing_data)

        # Save the updated data
        with open(file_path, "wb") as file:
            pickle.dump(data, file)

        output = template.render(upstreams=data, app_upstream=app_upstream)

        with open("nginx/config.conf", "w") as f:
            f.write(output)

    hostname = os.getenv("APP_HOSTNAME")
    return {
        "left_url": f"http://{hostname}/{container.name}-chat",
        "right_url": f"http://{hostname}/{container.name}-screen/vnc.html?&resize=scale&autoconnect=1&view_only=1&reconnect=1&reconnect_delay=2000",
    }


@app.get("/api/check_status")
async def check_status(left_url: str, right_url: str):
    def checkUrl(url):
        try:
            response = requests.get(url)
            return response.status_code == 200
        except requests.ConnectionError:
            return False

    return {"left": checkUrl(left_url), "right": checkUrl(right_url)}


@app.get("/list_containers")
async def list_containers(request: Request):
    user_token = request.headers.get("Authorization")

    # TODO: Implement logic to validate token and fetch user information.
    if not validate_token(user_token):
        return JSONResponse({"error": "User unauthorized"}, status_code=401)

    containers = client.containers.list()
    containers_info = []

    for container in containers:
        # fetch container information
        container_info = container.attrs

        # dictionary to map exposed container-host ports
        published_ports = {
            v["HostPort"]: {"host_port": v["HostPort"], "container_port": key}
            for key, value in container_info["NetworkSettings"]["Ports"].items()
            for v in value
            if v
        }

        container_data = {
            "id": container_info["Id"],
            "name": container_info["Name"],
            "image": container_info["Config"]["Image"],
            "state": container_info["State"]["Status"],
            "published_ports": published_ports,
        }

        containers_info.append(container_data)

    return containers_info


def validate_token(token):
    return True
