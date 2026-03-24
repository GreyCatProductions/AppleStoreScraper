import threading
from typing import List
from hcloud import Client
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.server_types import ServerType
from hcloud.servers.client import BoundServer
from hcloud.servers import Server
from dotenv import load_dotenv
import os

load_dotenv()
API_TOKEN = os.getenv("HETZNER_API_TOKEN")

_config_path = os.path.join(os.path.dirname(__file__), "..", "config", "user_data.sh")
with open(_config_path, "r") as f:
    USER_DATA = f.read()
if not API_TOKEN:
    raise EnvironmentError("HETZNER_API_TOKEN is not set")

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

client = Client(API_TOKEN)

MAX_SERVERS = 5
_server_count = 0
_server_count_lock = threading.Lock()


def create_server(ssh_keys: List[str]) -> tuple[BoundServer, str | None]:
    global _server_count
    with _server_count_lock:
        if _server_count >= MAX_SERVERS:
            raise RuntimeError(f"Server limit of {MAX_SERVERS} reached")
        name = f"server-{_server_count}"
        _server_count += 1
    print(
        f"Creating server: name={name}, ssh_keys={ssh_keys}, count={_server_count}/{MAX_SERVERS}"
    )

    registered_keys = []
    for i, ssh_key in enumerate(ssh_keys):
        existing = next(
            (
                k
                for k in client.ssh_keys.get_all()
                if k.public_key and k.public_key.split()[1] == ssh_key.split()[1]
            ),
            None,
        )
        if existing:
            registered_keys.append(existing)
        else:
            key_name = f"{name}-key-{i}"
            registered_keys.append(
                client.ssh_keys.create(name=key_name, public_key=ssh_key)
            )

    response = client.servers.create(
        image=Image(name="ubuntu-24.04"),
        location=Location(name="fsn1"),
        name=name,
        server_type=ServerType(name="cx23"),
        ssh_keys=registered_keys,
        start_after_create=True,
        user_data=USER_DATA,
    )
    response.action.wait_until_finished()
    print(f"Server creation done. server id={response.server.id}")
    return response.server, response.root_password


def delete_server(id: int) -> None:
    global _server_count
    action = client.servers.delete(
        server=Server(id=id),
    )
    action.wait_until_finished()
    with _server_count_lock:
        _server_count = max(0, _server_count - 1)


def get_server(id: int) -> BoundServer | None:
    server = client.servers.get_by_id(id)
    return server


def list_servers() -> List[BoundServer] | None:
    return client.servers.get_all()
