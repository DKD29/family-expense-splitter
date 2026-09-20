from decimal import Decimal, InvalidOperation
import math

USERS = ("Krishna", "Krishnamurty", "Karthik")

def to_decimal(value) -> Decimal:   
    """
    Convert a supported numeric value to Decimal safely.

    Integers, Decimals, and finite floats are supported.
    NaN and positive/negative infinity are rejected.
    Invalid numeric values raise ValueError.
    """
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Numeric value must be finite.")

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid numeric value.")

    if not result.is_finite():
        raise ValueError("Numeric value must be finite.")

    return result

MONEY_QUANTUM = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """
    Quantize a monetary value to two decimal places.

    Internal calculations may retain greater precision.
    This helper is intended for final monetary values.
    """
    return value.quantize(MONEY_QUANTUM)

def calculate_expense_shares(expense):
    """
    Calculate each person's responsibility for one Expense.

    The payer is completely independent from the split ratios.

    Returns:
        dict[str, Decimal]: Share owed by each user.
    """
    amount = to_decimal(expense["amount"])

    krishna_ratio = to_decimal(expense["krishna_ratio"])
    karthik_ratio = to_decimal(expense["karthik_ratio"])
    krishnamurty_ratio = to_decimal(expense["krishnamurty_ratio"])

    total_ratio = (
        krishna_ratio
        + karthik_ratio
        + krishnamurty_ratio
    )

    if total_ratio <= 0:
        raise ValueError("Total ratio must be greater than zero.")

    return {
        "Krishna": amount * krishna_ratio / total_ratio,
        "Krishnamurty": amount * krishnamurty_ratio / total_ratio,
        "Karthik": amount * karthik_ratio / total_ratio,
    }

def calculate_totals(expenses):
    """
    Calculate total expenses, total paid, total responsibility,
    and net balances from a list of expenses.

    Money Transfers are not accepted or used here.
    """

    total_expenses = Decimal("0")

    total_paid = {
        "Krishna": Decimal("0"),
        "Krishnamurty": Decimal("0"),
        "Karthik": Decimal("0"),
    }

    total_responsibility = {
        "Krishna": Decimal("0"),
        "Krishnamurty": Decimal("0"),
        "Karthik": Decimal("0"),
    }

    for expense in expenses:
        amount = to_decimal(expense["amount"])
        paid_by = expense["paid_by"]

        krishna_ratio = to_decimal(expense["krishna_ratio"])
        karthik_ratio = to_decimal(expense["karthik_ratio"])
        krishnamurty_ratio = to_decimal(expense["krishnamurty_ratio"])

        total_expenses += amount
        total_paid[paid_by] += amount

        total_ratio = (
            krishna_ratio
            + karthik_ratio
            + krishnamurty_ratio
        )

        total_responsibility["Krishna"] += (
            amount * krishna_ratio / total_ratio
        )

        total_responsibility["Karthik"] += (
            amount * karthik_ratio / total_ratio
        )

        total_responsibility["Krishnamurty"] += (
            amount * krishnamurty_ratio / total_ratio
        )

    net_balances = {
        "Krishna": total_paid["Krishna"] - total_responsibility["Krishna"],
        "Krishnamurty": (
            total_paid["Krishnamurty"]
            - total_responsibility["Krishnamurty"]
        ),
        "Karthik": total_paid["Karthik"] - total_responsibility["Karthik"],
    }

    return {
        "total_expenses": total_expenses,
        "total_paid": total_paid,
        "total_responsibility": total_responsibility,
        "net_balances": net_balances,
    }

def calculate_net_balances(expenses):
    """
    Calculate each person's net balance.

    Positive = the person is owed money.
    Negative = the person owes money.
    Zero = the person is settled.
    """

    totals = calculate_totals(expenses)

    total_paid = totals["total_paid"]
    total_responsibility = totals["total_responsibility"]

    return {
        "Krishna": (
            total_paid["Krishna"]
            - total_responsibility["Krishna"]
        ),
        "Krishnamurty": (
            total_paid["Krishnamurty"]
            - total_responsibility["Krishnamurty"]
        ),
        "Karthik": (
            total_paid["Karthik"]
            - total_responsibility["Karthik"]
        ),
    }

def calculate_settlement(net_balances):
    """
    Convert net balances into simplified payment instructions.

    Positive balance = creditor (is owed money).
    Negative balance = debtor (owes money).

    Returns a list of dictionaries with:
        from_user
        to_user
        amount
    """

    debtors = []
    creditors = []

    for user in USERS:
        balance = to_decimal(net_balances[user])

        if balance < 0:
            debtors.append({
                "user": user,
                "amount": -balance,
            })

        elif balance > 0:
            creditors.append({
                "user": user,
                "amount": balance,
            })

    settlements = []

    debtor_index = 0
    creditor_index = 0

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor = debtors[debtor_index]
        creditor = creditors[creditor_index]

        payment = min(
            debtor["amount"],
            creditor["amount"],
        )

        settlements.append({
            "from_user": debtor["user"],
            "to_user": creditor["user"],
            "amount": payment,
        })

        debtor["amount"] -= payment
        creditor["amount"] -= payment

        if debtor["amount"] == 0:
            debtor_index += 1

        if creditor["amount"] == 0:
            creditor_index += 1

    return settlements

def calculate_settlement(net_balances):
    """
    Convert net balances into a simplified set of payment instructions.

    Positive balance = user is owed money.
    Negative balance = user owes money.
    Zero balance = user is settled.

    Returns:
        list[dict]: Each dictionary contains:
            - from_user
            - to_user
            - amount
    """

    debtors = []
    creditors = []

    for user, balance in net_balances.items():
        balance = to_decimal(balance)

        if balance < 0:
            debtors.append(
                {
                    "user": user,
                    "amount": -balance,
                }
            )

        elif balance > 0:
            creditors.append(
                {
                    "user": user,
                    "amount": balance,
                }
            )

    settlements = []

    debtor_index = 0
    creditor_index = 0

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor = debtors[debtor_index]
        creditor = creditors[creditor_index]

        payment = min(debtor["amount"], creditor["amount"])

        payment = quantize_money(payment)

        if payment > 0:
            settlements.append(
                {
                    "from_user": debtor["user"],
                    "to_user": creditor["user"],
                    "amount": payment,
                }
            )

        debtor["amount"] -= payment
        creditor["amount"] -= payment

        debtor["amount"] = quantize_money(debtor["amount"])
        creditor["amount"] = quantize_money(creditor["amount"])

        if debtor["amount"] == 0:
            debtor_index += 1

        if creditor["amount"] == 0:
            creditor_index += 1

    return settlements

def calculate_expense_summary(expenses):
    """
    Calculate all expense-based financial information.

    Args:
        expenses: A list of expense dictionaries.

    Returns:
        dict containing:
            - total_expenses
            - total_paid
            - expense_shares
            - net_balances
            - settlements
            - everyone_settled
    """

    users = [
        "Krishna",
        "Krishnamurty",
        "Karthik",
    ]

    total_expenses = Decimal("0")

    total_paid = {
        user: Decimal("0")
        for user in users
    }

    expense_shares = []

    net_balances = {
        user: Decimal("0")
        for user in users
    }

    for expense in expenses:
        amount = to_decimal(expense["amount"])

        krishna_ratio = to_decimal(expense["krishna_ratio"])
        karthik_ratio = to_decimal(expense["karthik_ratio"])
        krishnamurty_ratio = to_decimal(
            expense["krishnamurty_ratio"]
        )

        total_ratio = (
            krishna_ratio
            + karthik_ratio
            + krishnamurty_ratio
        )

        shares = {
            "Krishna": amount * krishna_ratio / total_ratio,
            "Karthik": amount * karthik_ratio / total_ratio,
            "Krishnamurty": amount * krishnamurty_ratio / total_ratio,
        }

        expense_shares.append(
            {
                "id": expense.get("id"),
                "shares": shares,
            }
        )

        total_expenses += amount

        payer = expense["paid_by"]
        total_paid[payer] += amount

        for user in users:
            net_balances[user] += (
                -shares[user]
            )

        net_balances[payer] += amount

    total_expenses = quantize_money(total_expenses)

    total_paid = {
        user: quantize_money(amount)
        for user, amount in total_paid.items()
    }

    expense_shares = [
        {
            "id": item["id"],
            "shares": {
                user: quantize_money(share)
                for user, share in item["shares"].items()
            },
        }
        for item in expense_shares
    ]

    net_balances = {
        user: quantize_money(balance)
        for user, balance in net_balances.items()
    }

    settlements = calculate_settlement(net_balances)

    everyone_settled = len(settlements) == 0

    return {
        "total_expenses": total_expenses,
        "total_paid": total_paid,
        "expense_shares": expense_shares,
        "net_balances": net_balances,
        "settlements": settlements,
        "everyone_settled": everyone_settled,
    }