#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PYTHONPATH="$PWD"
streamlit run app/main.py
