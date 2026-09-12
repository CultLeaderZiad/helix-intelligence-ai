"""Identity of this process lifetime.

Background jobs run as ``asyncio`` tasks inside the web process, so they cannot
outlive it. Stamping each job with the boot id of the process that started it
makes that fact observable: on startup, any job still marked active whose
``owner_boot_id`` is not this one belonged to a process that no longer exists.
"""

import uuid

BOOT_ID: str = uuid.uuid4().hex
