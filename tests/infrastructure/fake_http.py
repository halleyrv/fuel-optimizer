import io
import json
from unittest import mock


def respond(*payloads):
    """Patch urlopen to return each payload in turn; an Exception payload is raised instead."""

    def fake_urlopen(request, timeout):
        payload = next(queue)
        if isinstance(payload, Exception):
            raise payload
        return io.BytesIO(json.dumps(payload).encode())

    queue = iter(payloads)
    return mock.patch("fuel_route.infrastructure.http.urlopen", side_effect=fake_urlopen)
