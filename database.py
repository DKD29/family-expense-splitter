"""Database access layer for the Family Trip Expense Splitter.

This module is the sole interface between the application and Supabase.

Phase 4 responsibilities:
- Provide controlled access to the Supabase database.
- Validate database-bound input before writes.
- Expose CRUD functions for Expenses and Money Transfers.
- Return predictable Python data.
- Convert database/provider failures into DatabaseError.

This module does NOT:
- perform expense calculations,
- calculate settlements,
- calculate totals,
- interact with Streamlit UI,
- implement authentication.
"""

from datetime import date

import streamlit as st
from supabase import Client, create_client


# ============================================================
# CONSTANTS
# ============================================================

VALID_USERS = (
    "Krishna",
    "Krishnamurty",
    "Karthik",
)


# ============================================================
# DATABASE ERROR
# ============================================================

class DatabaseError(Exception):
    """Raised when a database-layer operation fails."""


# ============================================================
# SUPABASE CONNECTION
# ============================================================

def _get_supabase_client() -> Client:
    """Return a configured Supabase client.

    Credentials are loaded from Streamlit secrets using:

        [supabase]
        url = "..."
        key = "..."

    Raises:
        DatabaseError: If configuration is missing or the client
            cannot be created.
    """
    try:
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]
    except Exception as exc:
        raise DatabaseError(
            "Supabase configuration is missing or invalid."
        ) from exc

    try:
        return create_client(supabase_url, supabase_key)
    except Exception as exc:
        raise DatabaseError(
            "Could not create the Supabase client."
        ) from exc


# ============================================================
# EXPENSE VALIDATION
# ============================================================

def _validate_expense(
    expense_date,
    description,
    amount,
    paid_by,
    krishna_ratio,
    karthik_ratio,
    krishnamurty_ratio,
):
    """Validate and normalize Expense input."""
    if not isinstance(expense_date, date):
        raise ValueError(
            "Expense date must be a calendar date."
        )

    if expense_date > date.today():
        raise ValueError(
            "Expense date cannot be in the future."
        )

    if not isinstance(description, str) or not description.strip():
        raise ValueError(
            "Expense description cannot be empty."
        )

    description = description.strip()

    if amount <= 0:
        raise ValueError(
            "Expense amount must be greater than zero."
        )

    if paid_by not in VALID_USERS:
        raise ValueError(
            "Invalid Expense payer."
        )

    ratios = (
        krishna_ratio,
        karthik_ratio,
        krishnamurty_ratio,
    )

    if any(ratio < 0 for ratio in ratios):
        raise ValueError(
            "Expense ratios cannot be negative."
        )

    if sum(ratios) <= 0:
        raise ValueError(
            "At least one Expense ratio must be greater than zero."
        )

    return (
        expense_date,
        description,
        amount,
        paid_by,
        krishna_ratio,
        karthik_ratio,
        krishnamurty_ratio,
    )


# ============================================================
# EXPENSE API
# ============================================================

def get_expenses():
    """Retrieve all Expense records.

    Returns:
        list[dict]: Expense records ordered newest first.

    Raises:
        DatabaseError: If retrieval fails.
    """
    try:
        response = (
            _get_supabase_client()
            .table("expenses")
            .select(
                "id, date, description, amount, paid_by, "
                "krishna_ratio, karthik_ratio, "
                "krishnamurty_ratio, created_at"
            )
            .order("date", desc=True)
            .order("created_at", desc=True)
            .execute()
        )

        return response.data or []

    except DatabaseError:
        raise

    except Exception as exc:
        raise DatabaseError(
            "Could not retrieve expenses."
        ) from exc


def add_expense(
    date,
    description,
    amount,
    paid_by,
    krishna_ratio,
    karthik_ratio,
    krishnamurty_ratio,
):
    """Create exactly one Expense record.

    Returns:
        dict: The newly created Expense record.

    Raises:
        ValueError: If input validation fails.
        DatabaseError: If the database operation fails.
    """
    (
        date,
        description,
        amount,
        paid_by,
        krishna_ratio,
        karthik_ratio,
        krishnamurty_ratio,
    ) = _validate_expense(
        date,
        description,
        amount,
        paid_by,
        krishna_ratio,
        karthik_ratio,
        krishnamurty_ratio,
    )

    expense_data = {
        "date": date.isoformat(),
        "description": description,
        "amount": amount,
        "paid_by": paid_by,
        "krishna_ratio": krishna_ratio,
        "karthik_ratio": karthik_ratio,
        "krishnamurty_ratio": krishnamurty_ratio,
    }

    try:
        response = (
            _get_supabase_client()
            .table("expenses")
            .insert(expense_data)
            .execute()
        )

        if not response.data:
            raise DatabaseError(
                "Could not add expense: no record was returned."
            )

        if len(response.data) != 1:
            raise DatabaseError(
                "Could not add expense: unexpected number "
                "of records returned."
            )

        return response.data[0]

    except DatabaseError:
        raise

    except Exception as exc:
        raise DatabaseError(
            "Could not add expense."
        ) from exc


def update_expense(
    expense_id,
    date,
    description,
    amount,
    paid_by,
    krishna_ratio,
    karthik_ratio,
    krishnamurty_ratio,
):
    """Update exactly one existing Expense record.

    Returns:
        dict: The updated Expense record.

    Raises:
        ValueError: If input validation fails.
        DatabaseError: If the database operation fails or the
            Expense does not exist.
    """
    (
        date,
        description,
        amount,
        paid_by,
        krishna_ratio,
        karthik_ratio,
        krishnamurty_ratio,
    ) = _validate_expense(
        date,
        description,
        amount,
        paid_by,
        krishna_ratio,
        karthik_ratio,
        krishnamurty_ratio,
    )

    expense_data = {
        "date": date.isoformat(),
        "description": description,
        "amount": amount,
        "paid_by": paid_by,
        "krishna_ratio": krishna_ratio,
        "karthik_ratio": karthik_ratio,
        "krishnamurty_ratio": krishnamurty_ratio,
    }

    try:
        response = (
            _get_supabase_client()
            .table("expenses")
            .update(expense_data)
            .eq("id", expense_id)
            .execute()
        )

        if not response.data:
            raise DatabaseError(
                "Could not update expense: Expense not found."
            )

        if len(response.data) != 1:
            raise DatabaseError(
                "Could not update expense: unexpected number "
                "of records affected."
            )

        return response.data[0]

    except DatabaseError:
        raise

    except Exception as exc:
        raise DatabaseError(
            "Could not update expense."
        ) from exc


def delete_expense(expense_id):
    """Permanently delete one Expense by ID.

    Returns:
        bool: True if deletion succeeded.

    Raises:
        DatabaseError: If deletion fails or the Expense does not exist.
    """
    try:
        response = (
            _get_supabase_client()
            .table("expenses")
            .delete()
            .eq("id", expense_id)
            .execute()
        )

        if not response.data:
            raise DatabaseError(
                "Could not delete expense: Expense not found."
            )

        if len(response.data) != 1:
            raise DatabaseError(
                "Could not delete expense: unexpected number "
                "of records affected."
            )

        return True

    except DatabaseError:
        raise

    except Exception as exc:
        raise DatabaseError(
            "Could not delete expense."
        ) from exc


# ============================================================
# MONEY TRANSFER VALIDATION
# ============================================================

def _validate_money_transfer(
    transfer_date,
    description,
    amount,
    from_user,
    to_user,
):
    """Validate and normalize Money Transfer input."""
    if not isinstance(transfer_date, date):
        raise ValueError(
            "Money Transfer date must be a calendar date."
        )

    if transfer_date > date.today():
        raise ValueError(
            "Money Transfer date cannot be in the future."
        )

    if not isinstance(description, str) or not description.strip():
        raise ValueError(
            "Money Transfer description cannot be empty."
        )

    description = description.strip()

    if amount <= 0:
        raise ValueError(
            "Money Transfer amount must be greater than zero."
        )

    if from_user not in VALID_USERS:
        raise ValueError(
            "Invalid Money Transfer sender."
        )

    if to_user not in VALID_USERS:
        raise ValueError(
            "Invalid Money Transfer receiver."
        )

    if from_user == to_user:
        raise ValueError(
            "Money Transfer sender and receiver must be different."
        )

    return (
        transfer_date,
        description,
        amount,
        from_user,
        to_user,
    )


# ============================================================
# MONEY TRANSFER API
# ============================================================

def get_money_transfers():
    """Retrieve all Money Transfer records.

    Returns:
        list[dict]: Money Transfer records ordered newest first.

    Raises:
        DatabaseError: If retrieval fails.
    """
    try:
        response = (
            _get_supabase_client()
            .table("money_transfers")
            .select(
                "id, date, description, amount, "
                "from_user, to_user, created_at"
            )
            .order("date", desc=True)
            .order("created_at", desc=True)
            .execute()
        )

        return response.data or []

    except DatabaseError:
        raise

    except Exception as exc:
        raise DatabaseError(
            "Could not retrieve money transfers."
        ) from exc


def add_money_transfer(
    date,
    description,
    amount,
    from_user,
    to_user,
):
    """Create exactly one Money Transfer record.

    Returns:
        dict: The newly created Money Transfer record.

    Raises:
        ValueError: If input validation fails.
        DatabaseError: If the database operation fails.
    """
    (
        date,
        description,
        amount,
        from_user,
        to_user,
    ) = _validate_money_transfer(
        date,
        description,
        amount,
        from_user,
        to_user,
    )

    transfer_data = {
        "date": date.isoformat(),
        "description": description,
        "amount": amount,
        "from_user": from_user,
        "to_user": to_user,
    }

    try:
        response = (
            _get_supabase_client()
            .table("money_transfers")
            .insert(transfer_data)
            .execute()
        )

        if not response.data:
            raise DatabaseError(
                "Could not add money transfer: "
                "no record was returned."
            )

        if len(response.data) != 1:
            raise DatabaseError(
                "Could not add money transfer: unexpected number "
                "of records returned."
            )

        return response.data[0]

    except DatabaseError:
        raise

    except Exception as exc:
        raise DatabaseError(
            "Could not add money transfer."
        ) from exc


def update_money_transfer(
    transfer_id,
    date,
    description,
    amount,
    from_user,
    to_user,
):
    """Update exactly one existing Money Transfer.

    Returns:
        dict: The updated Money Transfer record.

    Raises:
        ValueError: If input validation fails.
        DatabaseError: If the database operation fails or the
            Money Transfer does not exist.
    """
    (
        date,
        description,
        amount,
        from_user,
        to_user,
    ) = _validate_money_transfer(
        date,
        description,
        amount,
        from_user,
        to_user,
    )

    transfer_data = {
        "date": date.isoformat(),
        "description": description,
        "amount": amount,
        "from_user": from_user,
        "to_user": to_user,
    }

    try:
        response = (
            _get_supabase_client()
            .table("money_transfers")
            .update(transfer_data)
            .eq("id", transfer_id)
            .execute()
        )

        if not response.data:
            raise DatabaseError(
                "Could not update money transfer: "
                "Money Transfer not found."
            )

        if len(response.data) != 1:
            raise DatabaseError(
                "Could not update money transfer: unexpected "
                "number of records affected."
            )

        return response.data[0]

    except DatabaseError:
        raise

    except Exception as exc:
        raise DatabaseError(
            "Could not update money transfer."
        ) from exc


def delete_money_transfer(transfer_id):
    """Permanently delete one Money Transfer by ID.

    Returns:
        bool: True if deletion succeeded.

    Raises:
        DatabaseError: If deletion fails or the Money Transfer does
            not exist.
    """
    try:
        response = (
            _get_supabase_client()
            .table("money_transfers")
            .delete()
            .eq("id", transfer_id)
            .execute()
        )

        if not response.data:
            raise DatabaseError(
                "Could not delete money transfer: "
                "Money Transfer not found."
            )

        if len(response.data) != 1:
            raise DatabaseError(
                "Could not delete money transfer: unexpected "
                "number of records affected."
            )

        return True

    except DatabaseError:
        raise

    except Exception as exc:
        raise DatabaseError(
            "Could not delete money transfer."
        ) from exc