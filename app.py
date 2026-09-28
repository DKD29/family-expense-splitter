import streamlit as st
from datetime import date
from decimal import Decimal
import hashlib

from database import add_expense, get_expenses, DatabaseError
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
        placeholder="e.g. Hotel",
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
            step=0.1,
            format="%.2f",
            key="krishna_ratio",
        )

    with col2:
        karthik_ratio = st.number_input(
            "Karthik",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            key="karthik_ratio",
        )

    with col3:
        krishnamurty_ratio = st.number_input(
            "Krishnamurty",
            min_value=0.0,
            step=0.1,
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