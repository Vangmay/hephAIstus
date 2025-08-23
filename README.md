# Hello Script

This script prints the word "Hello" when run.

## Project Structure

- `HephAIstos.py` – Core tooling infrastructure (tool abstraction, registry, context/result classes).
- `HephAIstos_doc.md` – Auto‑generated module documentation.
- `HephAIstos_overview.md` – Human‑readable overview of the module.
- `inference.py` – Example usage of the Cerebras streaming chat API.
- `inference_doc.md` – Documentation for the inference script.
- `Blog/` – Notes and design thoughts.

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up your ```.env``` with the Cerebras API key.
3. Run `python inference.py` to see a streaming chat example.
