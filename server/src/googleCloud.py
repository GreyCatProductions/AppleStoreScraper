import sys
import uuid
from typing import Any

from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1

ZONE = "us-central1-a"

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

def list_instances(project_id: str) -> list[compute_v1.Instance]:
    client = compute_v1.InstancesClient()
    return list(client.list(project=project_id, zone=ZONE))


def delete_instance(project_id: str, instance_name: str) -> None:
    client = compute_v1.InstancesClient()
    operation = client.delete(project=project_id, zone=ZONE, instance=instance_name)
    wait_for_extended_operation(operation, "instance deletion")


def create_instance_from_template(
    project_id: str, template_name: str, instance_name: str | None = None, region: str = "us-central1"
) -> compute_v1.Instance:
    if instance_name is None:
        instance_name = f"scraper-{uuid.uuid4().hex[:8]}"
    client = compute_v1.InstancesClient()
    request = compute_v1.InsertInstanceRequest()
    request.project = project_id
    request.zone = ZONE
    request.source_instance_template = f"projects/{project_id}/regions/{region}/instanceTemplates/{template_name}"
    request.instance_resource = compute_v1.Instance(name=instance_name)

    operation = client.insert(request=request)
    wait_for_extended_operation(operation, "instance creation")
    return client.get(project=project_id, zone=ZONE, instance=instance_name)
