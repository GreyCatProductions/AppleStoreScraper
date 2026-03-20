from typing import List

from hcloud import Client
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.server_types import ServerType
from hcloud.ssh_keys import SSHKey
from hcloud.servers.client import BoundServer
from hcloud.servers import Server

API_TOKEN = #loads from dotenv

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}

client = Client("TOKEN") #TODO

def create_server(name: str, ssh_key: str) -> BoundServer:
    response = client.servers.create(
        image=Image(name="ubuntu-24.04"),
        location=Location(name="nbg1"),
        name=name,
        server_type=ServerType(name="cpx22"),
        ssh_keys=[SSHKey(name="key", public_key=ssh_key)],
        start_after_create=True,
        user_data="", #TODO
    )
    
    response.action.wait_until_finished()
    return response.server

def delete_server(id: int) -> None:
    action = client.servers.delete(
        server=Server(id=123),
    )
    action.wait_until_finished()

def get_server(id: int) -> BoundServer | None:
    server = client.servers.get_by_id(id)
    return server

def list_servers() -> List[BoundServer] | None:
    return client.servers.get_all()