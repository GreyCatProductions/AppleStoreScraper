import os
import sys
import uuid
from typing import Any

from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1
from dotenv import load_dotenv

load_dotenv()

_STARTUP_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "clientInit.sh"
)
_CREDENTIALS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "googleCredentials.json"
)

def wait_for_extended_operation(
    operation: ExtendedOperation, verbose_name: str = "operation", timeout: int = 300
) -> Any:
    """
    Waits for the extended (long-running) operation to complete.

    If the operation is successful, it will return its result.
    If the operation ends with an error, an exception will be raised.
    If there were any warnings during the execution of the operation
    they will be printed to sys.stderr.

    Args:
        operation: a long-running operation you want to wait on.
        verbose_name: (optional) a more verbose name of the operation,
            used only during error and warning reporting.
        timeout: how long (in seconds) to wait for operation to finish.
            If None, wait indefinitely.

    Returns:
        Whatever the operation.result() returns.

    Raises:
        This method will raise the exception received from `operation.exception()`
        or RuntimeError if there is no exception set, but there is an `error_code`
        set for the `operation`.

        In case of an operation taking longer than `timeout` seconds to complete,
        a `concurrent.futures.TimeoutError` will be raised.
    """
    result = operation.result(timeout=timeout)

    if operation.error_code:
        print(
            f"Error during {verbose_name}: [Code: {operation.error_code}]: {operation.error_message}",
            file=sys.stderr,
            flush=True,
        )
        print(f"Operation ID: {operation.name}", file=sys.stderr, flush=True)
        raise operation.exception() or RuntimeError(operation.error_message)

    if operation.warnings:
        print(f"Warnings during {verbose_name}:\n", file=sys.stderr, flush=True)
        for warning in operation.warnings:
            print(f" - {warning.code}: {warning.message}", file=sys.stderr, flush=True)

    return result


def start_stopped_instances(project_id: str) -> list[str]:
    client = compute_v1.InstancesClient()
    started = []
    for instance in list_instances(project_id):
        if instance.status == "TERMINATED":
            zone = _get_instance_zone(instance)
            operation = client.start(project=project_id, zone=zone, instance=instance.name)
            wait_for_extended_operation(operation, "instance start")
            started.append(instance.name)
    return started


def list_instances(project_id: str) -> list[compute_v1.Instance]:
    client = compute_v1.InstancesClient()
    result = []
    for _, scoped_list in client.aggregated_list(project=project_id):
        for instance in scoped_list.instances:
            if instance.labels.get("role") == "worker":
                result.append(instance)
    return result


def _get_instance_zone(instance: compute_v1.Instance) -> str:
    return instance.zone.split("/")[-1]


def delete_instance(project_id: str, instance_name: str) -> None:
    instances = list_instances(project_id)
    match = next((i for i in instances if i.name == instance_name), None)
    if not match:
        raise ValueError(f"Instance {instance_name} not found")
    zone = _get_instance_zone(match)
    client = compute_v1.InstancesClient()
    operation = client.delete(project=project_id, zone=zone, instance=instance_name)
    wait_for_extended_operation(operation, "instance deletion")


def create_instance_from_template(
    project_id: str,
    template_name: str,
    server_ip: str,
    port: int,
    google_drive_folder_id: str,
    api_key: str,
    zone: str,
    instance_name: str | None = None,
    ssh_keys: list[str] | None = None,
) -> compute_v1.Instance | None:
    
    if instance_name is None:
        instance_name = f"scraper-{uuid.uuid4().hex[:8]}"
    client = compute_v1.InstancesClient()
    request = compute_v1.InsertInstanceRequest()
    request.project = project_id
    request.zone = zone
    request.source_instance_template = (
        f"projects/{project_id}/global/instanceTemplates/{template_name}"
    )

    with open(_STARTUP_SCRIPT_PATH) as f:
        startup_script = f.read()

    with open(_CREDENTIALS_PATH) as f:
        credentials_json = f.read()

    metadata_items = [compute_v1.Items(key="startup-script", value=startup_script)]
    if ssh_keys:
        metadata_items.append(
            compute_v1.Items(key="ssh-keys", value="\n".join(ssh_keys))
        )
    metadata_items.append(compute_v1.Items(key="SERVER_IP", value=server_ip))
    metadata_items.append(compute_v1.Items(key="PORT", value=str(port)))
    metadata_items.append(compute_v1.Items(key="GOOGLE_DRIVE_FOLDER_ID", value=google_drive_folder_id))
    metadata_items.append(compute_v1.Items(key="GOOGLE_CREDENTIALS", value=credentials_json))
    metadata_items.append(compute_v1.Items(key="API_KEY", value=api_key))

    metadata = compute_v1.Metadata(items=metadata_items)

    request.instance_resource = compute_v1.Instance(
        name=instance_name, metadata=metadata, labels={"role": "worker"}
    )

    operation = client.insert(request=request)
    wait_for_extended_operation(operation, "instance creation")
    return client.get(project=project_id, zone=zone, instance=instance_name)
