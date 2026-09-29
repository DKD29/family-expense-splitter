import streamlit as st
from datetime import date
from decimal import Decimal
import hashlib

from database import (
    add_expense,
    get_expenses,
    update_expense,
    delete_expense,
    DatabaseError,
)
from calculations import calculate_totals, calculate_settlement


USERS = [
    "Krishna",
    "Krishnamurty",
    "Karthik",
]


def initialize_form_state():
    """Initialize expense form state once."""
    if "expense_date" not in st.session_state:
        st.session_state.expense_date = date.today()

    if "description" not in st.session_state:
        st.session_state.description = ""

    if "amount" not in st.session_state:
        st.session_state.amount = 0.0

    if "paid_by" not in st.session_state:
        st.session_state.paid_by = "Krishna"

    if "krishna_ratio" not in st.session_state:
        st.session_state.krishna_ratio = 1.0

    if "karthik_ratio" not in st.session_state:
        st.session_state.karthik_ratio = 1.0

    if "krishnamurty_ratio" not in st.session_state:
        st.session_state.krishnamurty_ratio = 1.0

    if "expenses" not in st.session_state:
        st.session_state.expenses = None

    if "last_successful_submission" not in st.session_state:
        st.session_state.last_successful_submission = None

def reset_expense_form():
    st.session_state.reset_expense_form = True


def reset_ratios():
    """Reset only the split ratios."""
    st.session_state.krishna_ratio = 1.0
    st.session_state.karthik_ratio = 1.0
    st.session_state.krishnamurty_ratio = 1.0

def create_submission_signature(
    expense_date,
    description,
    amount,
    paid_by,
    krishna_ratio,
    karthik_ratio,
    krishnamurty_ratio,
):
    """Create a deterministic signature for one expense submission."""

    submission_data = (
        f"{expense_date.isoformat()}|"
        f"{description.strip()}|"
        f"{Decimal(str(amount))}|"
        f"{paid_by}|"
        f"{Decimal(str(krishna_ratio))}|"
        f"{Decimal(str(karthik_ratio))}|"
        f"{Decimal(str(krishnamurty_ratio))}"
    )

    return hashlib.sha256(
        submission_data.encode("utf-8")
    ).hexdigest()

def load_expenses():
    """Load the latest expenses from Supabase."""
    try:
        st.session_state.expenses = get_expenses()
        return True

    except DatabaseError as exc:
        st.session_state.expenses = []
        st.error(str(exc))
        return False


initialize_form_state()

st.set_page_config(
    page_title="Family Trip Expense Splitter",
    layout="centered",
)


# ---------------------------------------------------------
# Load expenses from Supabase
# ---------------------------------------------------------

if st.session_state.expenses is None:
    load_expenses()


# ---------------------------------------------------------
# Page title
# ---------------------------------------------------------

st.title("Family Trip Expense Splitter")


# ---------------------------------------------------------
# Add Expense
# ---------------------------------------------------------

st.subheader("Add Expense")

if "reset_expense_form" not in st.session_state:
    st.session_state.reset_expense_form = False

if st.session_state.reset_expense_form:
    st.session_state.expense_date = date.today()
    st.session_state.description = ""
    st.session_state.amount = 0.0
    st.session_state.paid_by = "Krishna"
    st.session_state.krishna_ratio = 1.0
    st.session_state.karthik_ratio = 1.0
    st.session_state.krishnamurty_ratio = 1.0

    st.session_state.reset_expense_form = False

with st.form("expense_form"):

    expense_date = st.date_input(
        "Date",
        key="expense_date",
        max_value=date.today(),
    )

    description = st.text_input(
        "Description",
        key="description",
        placeholder="",
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
        karthik_ratio = st.number_input(
            "Karthik",
            min_value=0.0,
            step=0.10,
            format="%.2f",
            key="karthik_ratio",
        )

    with col3:
        krishnamurty_ratio = st.number_input(
            "Krishnamurty",
            min_value=0.0,
            step=0.10,
            format="%.2f",
            key="krishnamurty_ratio",
        )

    submitted = st.form_submit_button(
        "Add Expense",
        type="primary",
    )


# ---------------------------------------------------------
# Reset button
# ---------------------------------------------------------

st.button(
    "Reset to 1:1:1",
    on_click=reset_ratios,
)


# ---------------------------------------------------------
# Add Expense submission
# ---------------------------------------------------------

if submitted:

    # -----------------------------------------------------
    # Validate Add Expense form
    # -----------------------------------------------------

    if not description.strip():
        st.error("Description is required.")

    elif amount <= 0:
        st.error("Amount must be greater than ₹0.")

    elif expense_date > date.today():
        st.error("Expense date cannot be in the future.")

    elif (
        krishna_ratio < 0
        or karthik_ratio < 0
        or krishnamurty_ratio < 0
    ):
        st.error("Split ratios cannot be negative.")

    elif (
        krishna_ratio == 0
        and karthik_ratio == 0
        and krishnamurty_ratio == 0
    ):
        st.error("At least one split ratio must be greater than 0.")

    else:

        submission_signature = create_submission_signature(
            expense_date=expense_date,
            description=description,
            amount=amount,
            paid_by=paid_by,
            krishna_ratio=krishna_ratio,
            karthik_ratio=karthik_ratio,
            krishnamurty_ratio=krishnamurty_ratio,
        )

        if (
            submission_signature
            == st.session_state.last_successful_submission
        ):
            st.warning(
                "This expense has already been submitted."
            )

        else:

            try:
                add_expense(
                    date=expense_date,
                    description=description,
                    amount=Decimal(str(amount)),
                    paid_by=paid_by,
                    krishna_ratio=Decimal(str(krishna_ratio)),
                    karthik_ratio=Decimal(str(karthik_ratio)),
                    krishnamurty_ratio=Decimal(
                        str(krishnamurty_ratio)
                    ),
                )

            except ValueError as exc:
                st.error(str(exc))

            except DatabaseError as exc:
                st.error(str(exc))

            else:
                try:
                    updated_expenses = get_expenses()

                except DatabaseError as exc:
                    st.error(
                        "The expense was added, but the updated "
                        f"expense list could not be loaded. {exc}"
                    )

                else:
                    st.session_state.expenses = updated_expenses

                    st.session_state.last_successful_submission = (
                        submission_signature
                    )

                    st.success(
                        f"₹{amount:,.2f} expense added. "
                        f"{paid_by} paid."
                    )

                    reset_expense_form()

                    st.rerun()

# ---------------------------------------------------------
# Current totals and settlement
# ---------------------------------------------------------

expenses = st.session_state.expenses or []

if expenses:

    totals = calculate_totals(expenses)

    net_balances = totals["net_balances"]

    settlements = calculate_settlement(net_balances)

    st.divider()

    # -----------------------------------------------------
    # Current Settlement
    # -----------------------------------------------------

    st.subheader("Current Settlement")

    if not settlements:
        st.success("Everyone is settled up.")

    else:
        for settlement in settlements:

            from_user = settlement["from_user"]
            to_user = settlement["to_user"]
            settlement_amount = settlement["amount"]

            st.write(
                f"**{from_user}** owes **{to_user}** "
                f"₹{settlement_amount:,.2f}"
            )

    # -----------------------------------------------------
    # Total Paid
    # -----------------------------------------------------

    st.subheader("Total Paid")

    total_paid = totals["total_paid"]

    for user in USERS:
        st.write(
            f"**{user}:** ₹{total_paid[user]:,.2f}"
        )

    # -----------------------------------------------------
    # Total Expenses
    # -----------------------------------------------------

    st.subheader("Total Expenses")

    st.write(
        f"**₹{totals['total_expenses']:,.2f}**"
    )

else:

    st.divider()

    st.subheader("Current Settlement")
    st.write("No expenses yet.")

    st.subheader("Total Paid")

    for user in USERS:
        st.write(
            f"**{user}:** ₹0.00"
        )

    st.subheader("Total Expenses")
    st.write("**₹0.00**")

# ---------------------------------------------------------
# Expense History
# ---------------------------------------------------------

st.divider()

st.subheader("Expense History")

if not expenses:
    st.write("No expenses yet.")

else:
    for expense in expenses:

        expense_id = expense["id"]
        expense_date = expense["date"]
        description = expense["description"]
        amount = Decimal(str(expense["amount"]))
        paid_by = expense["paid_by"]

        krishna_ratio = Decimal(
            str(expense["krishna_ratio"])
        )

        karthik_ratio = Decimal(
            str(expense["karthik_ratio"])
        )

        krishnamurty_ratio = Decimal(
            str(expense["krishnamurty_ratio"])
        )

        edit_key = f"edit_expense_{expense_id}"

        if "editing_expense_id" not in st.session_state:
            st.session_state.editing_expense_id = None

        if "deleting_expense_id" not in st.session_state:
            st.session_state.deleting_expense_id = None

        with st.container(border=True):

            if (
                st.session_state.editing_expense_id
                == expense_id
            ):

                st.write("**Edit Expense**")

                with st.form(
                    f"edit_form_{expense_id}"
                ):

                    edit_date = st.date_input(
                        "Date",
                        value=date.fromisoformat(
                            expense_date
                        ),
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
                        index=USERS.index(paid_by),
                        key=f"edit_paid_by_{expense_id}",
                    )

                    st.write("**Split ratio**")

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        edit_krishna_ratio = st.number_input(
                            "Krishna",
                            min_value=0.0,
                            step=0.1,
                            format="%.2f",
                            value=float(krishna_ratio),
                            key=f"edit_krishna_ratio_{expense_id}",
                        )

                    with col2:
                        edit_karthik_ratio = st.number_input(
                            "Karthik",
                            min_value=0.0,
                            step=0.1,
                            format="%.2f",
                            value=float(karthik_ratio),
                            key=f"edit_karthik_ratio_{expense_id}",
                        )

                    with col3:
                        edit_krishnamurty_ratio = st.number_input(
                            "Krishnamurty",
                            min_value=0.0,
                            step=0.1,
                            format="%.2f",
                            value=float(krishnamurty_ratio),
                            key=f"edit_krishnamurty_ratio_{expense_id}",
                        )

                    save_edit = st.form_submit_button(
                        "Save Changes",
                        type="primary",
                    )

                    cancel_edit = st.form_submit_button(
                        "Cancel",
                    )

                if cancel_edit:
                    st.session_state.editing_expense_id = None
                    st.rerun()

                if save_edit:

                    if not edit_description.strip():
                        st.error(
                            "Description is required."
                        )

                    elif edit_amount <= 0:
                        st.error(
                            "Amount must be greater than ₹0."
                        )

                    elif edit_date > date.today():
                        st.error(
                            "Expense date cannot be in "
                            "the future."
                        )

                    elif (
                        edit_krishna_ratio < 0
                        or edit_karthik_ratio < 0
                        or edit_krishnamurty_ratio < 0
                    ):
                        st.error(
                            "Split ratios cannot be negative."
                        )

                    elif (
                        edit_krishna_ratio == 0
                        and edit_karthik_ratio == 0
                        and edit_krishnamurty_ratio == 0
                    ):
                        st.error(
                            "At least one split ratio must "
                            "be greater than 0."
                        )

                    else:

                        try:
                            update_expense(
                                expense_id=expense_id,
                                date=edit_date,
                                description=edit_description,
                                amount=Decimal(
                                    str(edit_amount)
                                ),
                                paid_by=edit_paid_by,
                                krishna_ratio=Decimal(
                                    str(edit_krishna_ratio)
                                ),
                                karthik_ratio=Decimal(
                                    str(edit_karthik_ratio)
                                ),
                                krishnamurty_ratio=Decimal(
                                    str(
                                        edit_krishnamurty_ratio
                                    )
                                ),
                            )

                        except ValueError as exc:
                            st.error(str(exc))

                        except DatabaseError as exc:
                            st.error(str(exc))

                        else:
                            try:
                                updated_expenses = (
                                    get_expenses()
                                )

                            except DatabaseError as exc:
                                st.error(
                                    "The expense was updated, "
                                    "but the updated expense "
                                    f"list could not be loaded. "
                                    f"{exc}"
                                )

                            else:
                                st.session_state.expenses = (
                                    updated_expenses
                                )

                                st.session_state.editing_expense_id = (
                                    None
                                )

                                st.success(
                                    "Expense updated successfully."
                                )

                                st.rerun()

            else:

                st.write(
                    f"**{description}**"
                )

                st.write(
                    f"{expense_date} · "
                    f"₹{amount:,.2f} · "
                    f"Paid by **{paid_by}**"
                )

                st.write("**Split ratio**")

                st.write(
                    f"Krishna: {krishna_ratio:g}  ·  "
                    f"Karthik: {karthik_ratio:g}  ·  "
                    f"Krishnamurty: "
                    f"{krishnamurty_ratio:g}"
                )

                if st.button(
                    "Edit",
                    key=edit_key,
                ):
                    st.session_state.editing_expense_id = expense_id
                    st.session_state.deleting_expense_id = None
                    st.rerun()

                if st.button(
                    "Delete",
                    key=f"delete_expense_{expense_id}",
                ):
                    st.session_state.deleting_expense_id = expense_id
                    st.session_state.editing_expense_id = None
                    st.rerun()

                if (
                    st.session_state.deleting_expense_id
                    == expense_id
                ):

                    st.warning(
                        f"Are you sure you want to permanently "
                        f"delete '{description}'?"
                    )

                    confirm_delete = st.button(
                        "Confirm Delete",
                        key=f"confirm_delete_{expense_id}",
                        type="primary",
                    )

                    cancel_delete = st.button(
                        "Cancel",
                        key=f"cancel_delete_{expense_id}",
                    )

                    if cancel_delete:
                        st.session_state.deleting_expense_id = (
                            None
                        )
                        st.rerun()

                    if confirm_delete:

                        try:
                            delete_expense(
                                expense_id
                            )

                        except DatabaseError as exc:
                            st.error(str(exc))

                        else:
                            try:
                                updated_expenses = (
                                    get_expenses()
                                )

                            except DatabaseError as exc:
                                st.error(
                                    "The expense was deleted, "
                                    "but the updated expense "
                                    f"list could not be loaded. "
                                    f"{exc}"
                                )

                            else:
                                st.session_state.expenses = (
                                    updated_expenses
                                )

                                st.session_state.deleting_expense_id = (
                                    None
                                )

                                st.success(
                                    "Expense deleted successfully."
                                )

                                st.rerun()