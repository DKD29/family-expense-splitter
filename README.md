# Family Trip Expense Splitter

A minimal family trip expense-splitting application built with Python, Streamlit, and Supabase.

## Current Status

**Phase 1 — Project Foundation**

The project currently contains the basic development foundation:

- Python virtual environment
- Streamlit
- Supabase Python client
- pytest
- Basic Streamlit application shell
- Supabase project configuration
- Secure local Streamlit secrets configuration
- Git/GitHub repository

Application functionality is intentionally not implemented yet.

## Technology

- Python
- Streamlit
- Supabase / PostgreSQL
- pytest
- Git / GitHub

## Local Development

### 1. Clone the repository

Clone the repository to your computer and enter the project directory.

### 2. Create the virtual environment

Create a Python virtual environment named `.venv`:

```text
python -m venv .venv
```

### 3. Activate the virtual environment

On Windows Command Prompt:

```text
.venv\Scripts\activate
```

### 4. Install dependencies

```text
python -m pip install -r requirements.txt
```

### 5. Configure Supabase secrets

Create:

```text
.streamlit/secrets.toml
```

with the required Supabase configuration:

```toml
[supabase]
url = "YOUR_SUPABASE_PROJECT_URL"
key = "YOUR_SUPABASE_API_KEY"
```

Do not commit this file to GitHub.

### 6. Run the application

```text
streamlit run app.py
```

The current application displays the basic project shell.

## Project Structure

```text
family-expense-splitter/
├── app.py
├── calculations.py
├── database.py
├── supabase_schema.sql
├── requirements.txt
├── README.md
├── .gitignore
│
├── .streamlit/
│   └── secrets.toml
│
└── tests/
    ├── test_calculations.py
    └── test_database.py
```

The `.venv/` directory also exists locally but is excluded from Git.

## Security

Supabase credentials are stored locally in:

```text
.streamlit/secrets.toml
```

This file is excluded from Git using `.gitignore` and must not be committed to the repository.

## Development Status

Future application functionality will be implemented in later development phases. The current Phase 1 foundation deliberately does not include expense tracking, money transfers, settlement calculations, or the production database schema.