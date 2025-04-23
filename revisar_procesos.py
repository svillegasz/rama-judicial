#!/usr/bin/env python3
import os
import sys
import logging

# Add the parent directory to the path so we can import our package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rama.workflows.procesos import revisar_procesos
from rama.utils.logging_utils import setup_logging

# Configure logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "revisar_procesos.log")
logger = setup_logging(log_level=logging.INFO, log_file=log_file)

if __name__ == "__main__":
    # Run the workflow
    revisar_procesos()
