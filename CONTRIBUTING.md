# Contributing to FinOps

Thank you for your interest in contributing to the FinOps Cloud Cost Forecasting project.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork locally.
3. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r cloud-cost-forecasting\requirements.txt
```

4. Install test dependencies:

```powershell
pip install pytest
```

## Running Tests

Run the application-specific tests:

```powershell
cd cloud-cost-forecasting
python -m pytest tests/ -v
```

Run the shared integration and regression tests from the repository root:

```powershell
python -m pytest tests/ -v
```

## Running the Application

```powershell
cd cloud-cost-forecasting
python -m streamlit run app.py
```

## Code Style

This project uses [EditorConfig](https://editorconfig.org/). See `.editorconfig` for details.

- Python: 4 spaces, UTF-8, LF line endings
- PowerShell: 4 spaces, UTF-8, LF line endings
- Markdown: 4 spaces, UTF-8, LF line endings

## Pull Requests

1. Create a feature branch from `master`.
2. Make your changes.
3. Run the test suite and verify all tests pass.
4. Open a pull request against `master`.

## License

This project is MIT licensed. See the `LICENSE` file (to be added by the repository owner).
