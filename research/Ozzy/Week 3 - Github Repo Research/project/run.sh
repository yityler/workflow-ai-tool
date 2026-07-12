#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Run tests (using pytest)
pytest src/

# Run main.py
python src/main.py
