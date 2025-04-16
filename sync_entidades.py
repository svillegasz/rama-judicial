#!/usr/bin/env python3
import os
import sys
import logging

# Add the parent directory to the path so we can import our package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rama.workflows.entidades import extraer_entidades

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    extraer_entidades()
