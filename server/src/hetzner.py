from typing import List
from hcloud import Client
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.server_types import ServerType
from hcloud.ssh_keys import SSHKey
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

def create_server(name: str, ssh_keys: List[str]) -> BoundServer:
    global _server_count
    if _server_count >= MAX_SERVERS:
        raise RuntimeError(f"Server limit of {MAX_SERVERS} reached")
    response = client.servers.create(
        image=Image(name="ubuntu-24.04"),
        location=Location(name="nbg1"),
        name=name,
        server_type=ServerType(name="cpx22"),
        ssh_keys=[SSHKey(name="key", public_key=ssh_key) for ssh_key in ssh_keys],
        start_after_create=True,
        user_data=USER_DATA,
    )

    response.action.wait_until_finished()
    _server_count += 1
    return response.server

def delete_server(id: int) -> None:
    global _server_count
    action = client.servers.delete(
        server=Server(id=123),
    )
    action.wait_until_finished()
    _server_count = max(0, _server_count - 1)

def get_server(id: int) -> BoundServer | None:
    server = client.servers.get_by_id(id)
    return server

def list_servers() -> List[BoundServer] | None:
    return client.servers.get_all()