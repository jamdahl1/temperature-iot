"""SQS consumer for the local Temperature IoT backends.

Importing this package does not read the environment or call AWS.
"""

from __future__ import annotations

import logging

logging.getLogger("temperature_demo.sqs_adapter").addHandler(logging.NullHandler())
