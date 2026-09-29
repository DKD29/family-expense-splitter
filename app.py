import hashlib
from datetime import date
from decimal import Decimal

import streamlit as st

from calculations import calculate_settlement, calculate_totals
from database import (
    DatabaseError,
    add_expense,
    add_money_transfer,
    delete_expense,
    delete_money_transfer,
    get_expenses,
    get_money_transfers,
    update_expense,
    update_money_transfer,
)


# ============================================================
# CONSTANTS
# ============================================================

USERS = [
    "Krishna",
    "Krishnamurty",
    "Karthik",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def as_date(value):
    """Convert a date or ISO date string into a date object."""
    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value))


def as_decimal(value):
    """Safely convert a numeric value to Decimal."""
    return Decimal(str(value))


def money(value):
    """
    Convert a numeric value to a JSON-safe float.

    Money Transfer calls use this because Supabase's JSON
    serialization does not accept Python Decimal objects directly.
    """
    return float(as_decimal(value))


def load_data(loader, state_key, error_message):
    """Load database data into session state."""
    try:
        st.session_state[state_key] = loader()
        return True

    except DatabaseError as exc:
        st.session_state[state_key] = []
        st.error(f"{error_message} {exc}")
        return False


def refresh_expenses():
    """Refresh expenses from Supabase."""
    return load_data(
        get_expenses,
        "expenses",
        "Could not load expenses.",
    )


def refresh_money_transfers():
    """Refresh Money Transfers from Supabase."""
    return load_data(
        get_money_transfers,
        "money_transfers",
        "Could not load Money Transfers.",
    )


def calculate_combined_net_balances(expenses, money_transfers):
    """
    Calculate settlement balances from Expenses and Money Transfers.

    Expenses create the original balances. A Money Transfer reduces
    what the sender still owes and reduces what the receiver is owed.
    """
    net_balances = {
        user: Decimal("0")
        for user in USERS
    }

    if expenses:
        totals = calculate_totals(expenses)

        for user in USERS:
            net_balances[user] = as_decimal(
                totals["net_balances"].get(user, 0)
            )

    for transfer in money_transfers:
        from_user = transfer["from_user"]
        to_user = transfer["to_user"]
        amount = as_decimal(transfer["amount"])

        net_balances[from_user] += amount
        net_balances[to_user] -= amount

    return net_balances


def user_index(user):
    """Return a safe index for a user select box."""
    if user in USERS:
        return USERS.index(user)

    return 0


# ============================================================
# SESSION STATE
# ============================================================

def initialize_state():
    """
    Initialize persistent session-state values before widgets exist.
    """
    defaults = {
        # Database data
        "expenses": None,
        "money_transfers": None,

        # UI selectors
        "add_record_type": "Expense",
        "history_filter": "All",

        # Add Expense form
        "expense_date": date.today(),
        "description": "",
        "amount": 0.0,
        "paid_by": "Krishna",
        "krishna_ratio": 1.0,
        "karthik_ratio": 1.0,
        "krishnamurty_ratio": 1.0,

        # Add Money Transfer form
        "money_transfer_date": date.today(),
        "money_transfer_description": "",
        "money_transfer_amount": 0.0,
        "money_transfer_from_user": "Krishna",
        "money_transfer_to_user": "Krishnamurty",

        # Reset flags
        "reset_expense_form": False,
        "reset_money_transfer_form": False,

        # Duplicate-submit protection
        "last_successful_submission": None,
        "last_successful_transfer_submission": None,

        # Expense editing/deleting
        "editing_expense_id": None,
        "deleting_expense_id": None,

        # Money Transfer editing/deleting
        "editing_money_transfer_id": None,
        "deleting_money_transfer_id": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_pending_resets():
    """
    Apply resets before widgets are created.

    This prevents StreamlitWidgetAlreadyInstantiatedError.
    """
    if st.session_state.reset_expense_form:
        st.session_state.expense_date = date.today()
        st.session_state.description = ""
        st.session_state.amount = 0.0
        st.session_state.paid_by = "Krishna"
        st.session_state.krishna_ratio = 1.0
        st.session_state.karthik_ratio = 1.0
        st.session_state.krishnamurty_ratio = 1.0
        st.session_state.reset_expense_form = False

    if st.session_state.reset_money_transfer_form:
        st.session_state.money_transfer_date = date.today()
        st.session_state.money_transfer_description = ""
        st.session_state.money_transfer_amount = 0.0
        st.session_state.money_transfer_from_user = "Krishna"
        st.session_state.money_transfer_to_user = "Krishnamurty"
        st.session_state.reset_money_transfer_form = False


def reset_ratios():
    """Reset only the Add Expense ratios to 1:1:1."""
    st.session_state.krishna_ratio = 1.0
    st.session_state.karthik_ratio = 1.0
    st.session_state.krishnamurty_ratio = 1.0


# ============================================================
# SUBMISSION SIGNATURES
# ============================================================

def expense_signature(
    expense_date,
    description,
    amount,
    paid_by,
    krishna_ratio,
    karthik_ratio,
    krishnamurty_ratio,
):
    """Create a deterministic signature for an Expense."""
    data = (
        f"{as_date(expense_date).isoformat()}|"
        f"{description.strip()}|"
        f"{as_decimal(amount)}|"
        f"{paid_by}|"
        f"{as_decimal(krishna_ratio)}|"
        f"{as_decimal(karthik_ratio)}|"
        f"{as_decimal(krishnamurty_ratio)}"
    )

    return hashlib.sha256(
        data.encode("utf-8")
    ).hexdigest()


def transfer_signature(
    transfer_date,
    description,
    amount,
    from_user,
    to_user,
):
    """Create a deterministic signature for a Money Transfer."""
    data = (
        f"{as_date(transfer_date).isoformat()}|"
        f"{description.strip()}|"
        f"{as_decimal(amount)}|"
        f"{from_user}|"
        f"{to_user}"
    )

    return hashlib.sha256(
        data.encode("utf-8")
    ).hexdigest()


# ============================================================
# VALIDATION
# ============================================================

def validate_expense_form(
    expense_date,
    description,
    amount,
    krishna_ratio,
    karthik_ratio,
    krishnamurty_ratio,
):
    """Validate an Expense form."""
    if not description.strip():
        return "Description is required."

    if amount <= 0:
        return "Amount must be greater than ₹0."

    if expense_date > date.today():
        return "Expense date cannot be in the future."

    if (
        krishna_ratio < 0
        or karthik_ratio < 0
        or krishnamurty_ratio < 0
    ):
        return "Split ratios cannot be negative."

    if (
        krishna_ratio == 0
        and karthik_ratio == 0
        and krishnamurty_ratio == 0
    ):
        return "At least one split ratio must be greater than 0."

    return None


def validate_transfer_form(
    transfer_date,
    description,
    amount,
    from_user,
    to_user,
):
    """Validate a Money Transfer form."""
    if not description.strip():
        return "Description is required."

    if amount <= 0:
        return "Amount must be greater than ₹0."

    if transfer_date > date.today():
        return "Money Transfer date cannot be in the future."

    if from_user == to_user:
        return "From and To must be different people."

    return None


# ============================================================
# HISTORY RENDERING
# ============================================================

def render_expense_history(expenses):
    """Render editable Expense history cards."""
    if not expenses:
        st.write("No expenses yet.")
        return

    for expense in expenses:
        expense_id = expense["id"]
        expense_date = as_date(expense["date"])
        description = expense["description"]
        amount = as_decimal(expense["amount"])
        paid_by = expense["paid_by"]
        krishna_ratio = as_decimal(expense["krishna_ratio"])
        karthik_ratio = as_decimal(expense["karthik_ratio"])
        krishnamurty_ratio = as_decimal(
            expense["krishnamurty_ratio"]
        )

        with st.container(border=True):
            if st.session_state.editing_expense_id == expense_id:
                st.write("**Edit Expense**")

                with st.form(f"edit_expense_form_{expense_id}"):
                    edit_date = st.date_input(
                        "Date",
                        value=expense_date,
                        max_value=date.today(),
                        key=f"edit_date_{expense_id}",
                    )

                    edit_description = st.text_input(
                        "Description",
                        value=description,
                        key=f"edit_description_{expense_id}",
                    )

                    edit_amount = st.number_input(
                        "Amount (₹)",
                        min_value=0.0,
                        step=1.0,
                        format="%.2f",
                        value=float(amount),
                        key=f"edit_amount_{expense_id}",
                    )

                    edit_paid_by = st.selectbox(
                        "Paid by",
                        USERS,
                        index=user_index(paid_by),
                        key=f"edit_paid_by_{expense_id}",
                    )

                    st.write("Split ratio")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        edit_krishna_ratio = st.number_input(
                            "Krishna",
                            min_value=0.0,
                            step=0.10,
                            format="%.2f",
                            value=float(krishna_ratio),
                            key=f"edit_krishna_ratio_{expense_id}",
                        )

                    with col2:
                        edit_karthik_ratio = st.number_input(
                            "Karthik",
                            min_value=0.0,
                            step=0.10,
                            format="%.2f",
                            value=float(karthik_ratio),
                            key=f"edit_karthik_ratio_{expense_id}",
                        )

                    with col3:
                        edit_krishnamurty_ratio = st.number_input(
                            "Krishnamurty",
                            min_value=0.0,
                            step=0.10,
                            format="%.2f",
                            value=float(krishnamurty_ratio),
                            key=(
                                f"edit_krishnamurty_ratio_"
                                f"{expense_id}"
                            ),
                        )

                    save_expense = st.form_submit_button(
                        "Save Changes",
                        type="primary",
                    )
                    cancel_expense = st.form_submit_button("Cancel")

                if cancel_expense:
                    st.session_state.editing_expense_id = None
                    st.rerun()

                if save_expense:
                    error = validate_expense_form(
                        edit_date,
                        edit_description,
                        edit_amount,
                        edit_krishna_ratio,
                        edit_karthik_ratio,
                        edit_krishnamurty_ratio,
                    )

                    if error:
                        st.error(error)

                    else:
                        try:
                            update_expense(
                                expense_id=expense_id,
                                date=edit_date,
                                description=edit_description,
                                amount=as_decimal(edit_amount),
                                paid_by=edit_paid_by,
                                krishna_ratio=as_decimal(
                                    edit_krishna_ratio
                                ),
                                karthik_ratio=as_decimal(
                                    edit_karthik_ratio
                                ),
                                krishnamurty_ratio=as_decimal(
                                    edit_krishnamurty_ratio
                                ),
                            )

                            st.session_state.expenses = get_expenses()

                        except ValueError as exc:
                            st.error(str(exc))

                        except DatabaseError as exc:
                            st.error(str(exc))

                        else:
                            st.session_state.editing_expense_id = None
                            st.success("Expense updated.")
                            st.rerun()

            elif st.session_state.deleting_expense_id == expense_id:
                st.warning(
                    "Delete this expense permanently? "
                    "This cannot be undone."
                )

                confirm_col, cancel_col = st.columns(2)

                with confirm_col:
                    confirm_delete = st.button(
                        "Confirm Delete",
                        key=f"confirm_delete_expense_{expense_id}",
                        type="primary",
                    )

                with cancel_col:
                    cancel_delete = st.button(
                        "Cancel",
                        key=f"cancel_delete_expense_{expense_id}",
                    )

                if cancel_delete:
                    st.session_state.deleting_expense_id = None
                    st.rerun()

                if confirm_delete:
                    try:
                        delete_expense(expense_id)
                        st.session_state.expenses = get_expenses()

                    except DatabaseError as exc:
                        st.error(str(exc))

                    else:
                        st.session_state.deleting_expense_id = None
                        st.success("Expense deleted.")
                        st.rerun()

            else:
                st.write(f"**{description}**")
                st.caption(
                    f"{expense_date.strftime('%d %b %Y')} · "
                    f"{paid_by} paid"
                )
                st.write(f"₹{amount:,.2f}")
                st.caption(
                    "Split ratio — "
                    f"Krishna: {krishna_ratio}, "
                    f"Krishnamurty: {krishnamurty_ratio}, "
                    f"Karthik: {karthik_ratio}"
                )

                edit_col, delete_col = st.columns(2)

                with edit_col:
                    if st.button(
                        "Edit",
                        key=f"edit_expense_{expense_id}",
                    ):
                        st.session_state.editing_expense_id = expense_id
                        st.session_state.deleting_expense_id = None
                        st.rerun()

                with delete_col:
                    if st.button(
                        "Delete",
                        key=f"delete_expense_{expense_id}",
                    ):
                        st.session_state.deleting_expense_id = expense_id
                        st.session_state.editing_expense_id = None
                        st.rerun()


def render_money_transfer_history(money_transfers):
    """Render editable Money Transfer history cards."""
    if not money_transfers:
        st.write("No money transfers yet.")
        return

    for transfer in money_transfers:
        transfer_id = transfer["id"]
        transfer_date = as_date(transfer["date"])
        description = transfer["description"]
        amount = as_decimal(transfer["amount"])
        from_user = transfer["from_user"]
        to_user = transfer["to_user"]

        with st.container(border=True):
            if (
                st.session_state.editing_money_transfer_id
                == transfer_id
            ):
                st.write("**Edit Money Transfer**")

                with st.form(
                    f"edit_money_transfer_form_{transfer_id}"
                ):
                    edit_date = st.date_input(
                        "Date",
                        value=transfer_date,
                        max_value=date.today(),
                        key=f"edit_transfer_date_{transfer_id}",
                    )

                    edit_description = st.text_input(
                        "Description",
                        value=description,
                        key=f"edit_transfer_description_{transfer_id}",
                    )

                    edit_amount = st.number_input(
                        "Amount (₹)",
                        min_value=0.0,
                        step=1.0,
                        format="%.2f",
                        value=float(amount),
                        key=f"edit_transfer_amount_{transfer_id}",
                    )

                    edit_from_user = st.selectbox(
                        "From",
                        USERS,
                        index=user_index(from_user),
                        key=f"edit_transfer_from_{transfer_id}",
                    )

                    edit_to_user = st.selectbox(
                        "To",
                        USERS,
                        index=user_index(to_user),
                        key=f"edit_transfer_to_{transfer_id}",
                    )

                    save_transfer = st.form_submit_button(
                        "Save Changes",
                        type="primary",
                    )
                    cancel_transfer = st.form_submit_button("Cancel")

                if cancel_transfer:
                    st.session_state.editing_money_transfer_id = None
                    st.rerun()

                if save_transfer:
                    error = validate_transfer_form(
                        edit_date,
                        edit_description,
                        edit_amount,
                        edit_from_user,
                        edit_to_user,
                    )

                    if error:
                        st.error(error)

                    else:
                        try:
                            update_money_transfer(
                                transfer_id=transfer_id,
                                date=edit_date,
                                description=edit_description,
                                amount=money(edit_amount),
                                from_user=edit_from_user,
                                to_user=edit_to_user,
                            )

                            st.session_state.money_transfers = (
                                get_money_transfers()
                            )

                        except ValueError as exc:
                            st.error(str(exc))

                        except DatabaseError as exc:
                            st.error(str(exc))

                        else:
                            st.session_state.editing_money_transfer_id = None
                            st.success("Money Transfer updated.")
                            st.rerun()

            elif (
                st.session_state.deleting_money_transfer_id
                == transfer_id
            ):
                st.warning(
                    "Delete this Money Transfer permanently? "
                    "This cannot be undone."
                )

                confirm_col, cancel_col = st.columns(2)

                with confirm_col:
                    confirm_delete = st.button(
                        "Confirm Delete",
                        key=f"confirm_delete_transfer_{transfer_id}",
                        type="primary",
                    )

                with cancel_col:
                    cancel_delete = st.button(
                        "Cancel",
                        key=f"cancel_delete_transfer_{transfer_id}",
                    )

                if cancel_delete:
                    st.session_state.deleting_money_transfer_id = None
                    st.rerun()

                if confirm_delete:
                    try:
                        delete_money_transfer(transfer_id)

                        st.session_state.money_transfers = (
                            get_money_transfers()
                        )

                    except DatabaseError as exc:
                        st.error(str(exc))

                    else:
                        st.session_state.deleting_money_transfer_id = None
                        st.success("Money Transfer deleted.")
                        st.rerun()

            else:
                st.write(f"**{description}**")
                st.caption(
                    f"{transfer_date.strftime('%d %b %Y')} · "
                    f"{from_user} → {to_user}"
                )
                st.write(f"₹{amount:,.2f}")

                edit_col, delete_col = st.columns(2)

                with edit_col:
                    if st.button(
                        "Edit",
                        key=f"edit_transfer_{transfer_id}",
                    ):
                        st.session_state.editing_money_transfer_id = (
                            transfer_id
                        )
                        st.session_state.deleting_money_transfer_id = (
                            None
                        )
                        st.rerun()

                with delete_col:
                    if st.button(
                        "Delete",
                        key=f"delete_transfer_{transfer_id}",
                    ):
                        st.session_state.deleting_money_transfer_id = (
                            transfer_id
                        )
                        st.session_state.editing_money_transfer_id = None
                        st.rerun()


# ============================================================
# PAGE CONFIGURATION AND INITIALIZATION
# ============================================================

st.set_page_config(
    page_title="Family Trip Expense Splitter",
    layout="centered",
)

initialize_state()
apply_pending_resets()

if st.session_state.expenses is None:
    refresh_expenses()

if st.session_state.money_transfers is None:
    refresh_money_transfers()

expenses = st.session_state.expenses or []
money_transfers = st.session_state.money_transfers or []

st.title("Family Trip Expense Splitter")


# ============================================================
# 1. SETTLEMENT SUMMARY
# ============================================================

st.subheader("Settlement Summary")

if expenses or money_transfers:
    combined_net_balances = calculate_combined_net_balances(
        expenses,
        money_transfers,
    )

    settlements = calculate_settlement(combined_net_balances)

    if settlements:
        for settlement in settlements:
            st.write(
                f"**{settlement['from_user']}** owes "
                f"**{settlement['to_user']}** "
                f"₹{settlement['amount']:,.2f}"
            )
    else:
        st.success("Everyone is settled up.")
else:
    st.write("No expenses or money transfers yet.")


# ============================================================
# 2. ADD
# ============================================================

st.divider()
st.subheader("Add")

record_type = st.selectbox(
    "What do you want to add?",
    ["Expense", "Money Transfer"],
    key="add_record_type",
)

if record_type == "Expense":
    with st.form("expense_form"):
        expense_date = st.date_input(
            "Date",
            key="expense_date",
            max_value=date.today(),
        )

        description = st.text_input(
            "Description",
            key="description",
        )

        amount = st.number_input(
            "Amount (₹)",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            key="amount",
        )

        paid_by = st.selectbox(
            "Paid by",
            USERS,
            key="paid_by",
        )

        st.write("Split ratio")

        col1, col2, col3 = st.columns(3)

        with col1:
            krishna_ratio = st.number_input(
                "Krishna",
                min_value=0.0,
                step=0.10,
                format="%.2f",
                key="krishna_ratio",
            )

        with col2:
            krishnamurty_ratio = st.number_input(
                "Krishnamurty",
                min_value=0.0,
                step=0.10,
                format="%.2f",
                key="krishnamurty_ratio",
            )

        with col3:
            karthik_ratio = st.number_input(
                "Karthik",
                min_value=0.0,
                step=0.10,
                format="%.2f",
                key="karthik_ratio",
            )

        expense_submitted = st.form_submit_button(
            "Add Expense",
            type="primary",
        )

    st.button(
        "Reset split to 1:1:1",
        on_click=reset_ratios,
    )

    if expense_submitted:
        error = validate_expense_form(
            expense_date,
            description,
            amount,
            krishna_ratio,
            karthik_ratio,
            krishnamurty_ratio,
        )

        if error:
            st.error(error)

        else:
            signature = expense_signature(
                expense_date,
                description,
                amount,
                paid_by,
                krishna_ratio,
                karthik_ratio,
                krishnamurty_ratio,
            )

            if (
                signature
                == st.session_state.last_successful_submission
            ):
                st.warning("This expense has already been submitted.")

            else:
                try:
                    add_expense(
                        date=expense_date,
                        description=description,
                        amount=as_decimal(amount),
                        paid_by=paid_by,
                        krishna_ratio=as_decimal(krishna_ratio),
                        karthik_ratio=as_decimal(karthik_ratio),
                        krishnamurty_ratio=as_decimal(
                            krishnamurty_ratio
                        ),
                    )

                    st.session_state.expenses = get_expenses()

                except ValueError as exc:
                    st.error(str(exc))

                except DatabaseError as exc:
                    st.error(str(exc))

                else:
                    st.session_state.last_successful_submission = (
                        signature
                    )
                    st.session_state.reset_expense_form = True
                    st.success(
                        f"₹{amount:,.2f} expense added. "
                        f"{paid_by} paid."
                    )
                    st.rerun()

else:
    with st.form("money_transfer_form"):
        transfer_date = st.date_input(
            "Date",
            key="money_transfer_date",
            max_value=date.today(),
        )

        transfer_description = st.text_input(
            "Description",
            key="money_transfer_description",
        )

        transfer_amount = st.number_input(
            "Amount (₹)",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            key="money_transfer_amount",
        )

        from_user = st.selectbox(
            "From",
            USERS,
            key="money_transfer_from_user",
        )

        to_user = st.selectbox(
            "To",
            USERS,
            key="money_transfer_to_user",
        )

        transfer_submitted = st.form_submit_button(
            "Add Money Transfer",
            type="primary",
        )

    if transfer_submitted:
        error = validate_transfer_form(
            transfer_date,
            transfer_description,
            transfer_amount,
            from_user,
            to_user,
        )

        if error:
            st.error(error)

        else:
            signature = transfer_signature(
                transfer_date,
                transfer_description,
                transfer_amount,
                from_user,
                to_user,
            )

            if (
                signature
                == st.session_state.last_successful_transfer_submission
            ):
                st.warning(
                    "This Money Transfer has already been submitted."
                )

            else:
                try:
                    add_money_transfer(
                        date=transfer_date,
                        description=transfer_description,
                        amount=money(transfer_amount),
                        from_user=from_user,
                        to_user=to_user,
                    )

                    st.session_state.money_transfers = (
                        get_money_transfers()
                    )

                except ValueError as exc:
                    st.error(str(exc))

                except DatabaseError as exc:
                    st.error(str(exc))

                else:
                    st.session_state.last_successful_transfer_submission = (
                        signature
                    )
                    st.session_state.reset_money_transfer_form = True
                    st.success(
                        f"₹{transfer_amount:,.2f} transferred "
                        f"from {from_user} to {to_user}."
                    )
                    st.rerun()


# ============================================================
# 3. HISTORY
# ============================================================

st.divider()
st.subheader("History")

history_filter = st.selectbox(
    "Show",
    ["All", "Expenses", "Money Transfers"],
    key="history_filter",
)

if history_filter in ["All", "Expenses"]:
    if history_filter == "All":
        st.markdown("#### Expenses")

    render_expense_history(expenses)

if history_filter == "All":
    st.divider()

if history_filter in ["All", "Money Transfers"]:
    if history_filter == "All":
        st.markdown("#### Money Transfers")

    render_money_transfer_history(money_transfers)