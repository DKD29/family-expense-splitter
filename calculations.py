from decimal import Decimal, InvalidOperation
import math


USERS = (
    "Krishna",
    "Krishnamurty",
    "Karthik",
)

MONEY_QUANTUM = Decimal("0.01")


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
    krishnamurty_ratio = to_decimal(
        expense["krishnamurty_ratio"]
    )

    total_ratio = (
        krishna_ratio
        + karthik_ratio
        + krishnamurty_ratio
    )

    if total_ratio <= 0:
        raise ValueError(
            "Total ratio must be greater than zero."
        )

    return {
        "Krishna": (
            amount * krishna_ratio / total_ratio
        ),
        "Krishnamurty": (
            amount * krishnamurty_ratio / total_ratio
        ),
        "Karthik": (
            amount * karthik_ratio / total_ratio
        ),
    }


def apply_money_transfers(
    net_balances,
    money_transfers,
):
    """
    Apply Money Transfers to existing net balances.

    A transfer from A to B means:
        - A has paid money toward the settlement.
        - A's balance increases by the transfer amount.
        - B's balance decreases by the transfer amount.

    Money Transfers affect settlement only.

    They do NOT affect:
        - total_expenses
        - total_paid
        - total_responsibility

    Args:
        net_balances: dict[str, Decimal]
        money_transfers: list[dict]

    Returns:
        dict[str, Decimal]: Updated net balances.
    """
    updated_balances = {
        user: to_decimal(net_balances[user])
        for user in USERS
    }

    for transfer in money_transfers:
        amount = to_decimal(transfer["amount"])
        from_user = transfer["from_user"]
        to_user = transfer["to_user"]

        if from_user not in USERS:
            raise ValueError(
                "Invalid Money Transfer sender."
            )

        if to_user not in USERS:
            raise ValueError(
                "Invalid Money Transfer receiver."
            )

        if from_user == to_user:
            raise ValueError(
                "Money Transfer sender and receiver "
                "must be different."
            )

        if amount <= 0:
            raise ValueError(
                "Money Transfer amount must be greater than zero."
            )

        updated_balances[from_user] += amount
        updated_balances[to_user] -= amount

    return updated_balances


def calculate_totals(
    expenses,
    money_transfers=None,
):
    """
    Calculate expense totals and final net balances.

    Money Transfers affect only net_balances.

    They do NOT affect:
        - total_expenses
        - total_paid
        - total_responsibility

    Args:
        expenses: List of Expense records.
        money_transfers: Optional list of Money Transfer records.

    Returns:
        dict containing:
            - total_expenses
            - total_paid
            - total_responsibility
            - net_balances
    """
    if money_transfers is None:
        money_transfers = []

    total_expenses = Decimal("0")

    total_paid = {
        user: Decimal("0")
        for user in USERS
    }

    total_responsibility = {
        user: Decimal("0")
        for user in USERS
    }

    for expense in expenses:
        amount = to_decimal(expense["amount"])
        paid_by = expense["paid_by"]

        if paid_by not in USERS:
            raise ValueError(
                "Invalid expense payer."
            )

        shares = calculate_expense_shares(expense)

        total_expenses += amount
        total_paid[paid_by] += amount

        for user in USERS:
            total_responsibility[user] += shares[user]

    expense_net_balances = {
        user: (
            total_paid[user]
            - total_responsibility[user]
        )
        for user in USERS
    }

    net_balances = apply_money_transfers(
        expense_net_balances,
        money_transfers,
    )

    return {
        "total_expenses": total_expenses,
        "total_paid": total_paid,
        "total_responsibility": total_responsibility,
        "net_balances": net_balances,
    }


def calculate_net_balances(
    expenses,
    money_transfers=None,
):
    """
    Calculate final net balances.

    Positive = the person is owed money.
    Negative = the person owes money.
    Zero = the person is settled.

    Money Transfers are applied after expense balances
    are calculated.
    """
    totals = calculate_totals(
        expenses,
        money_transfers,
    )

    return totals["net_balances"]


def calculate_settlement(net_balances):
    """
    Convert net balances into simplified payment instructions.

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

    for user in USERS:
        balance = to_decimal(net_balances[user])

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

    while (
        debtor_index < len(debtors)
        and creditor_index < len(creditors)
    ):
        debtor = debtors[debtor_index]
        creditor = creditors[creditor_index]

        payment = min(
            debtor["amount"],
            creditor["amount"],
        )

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

        debtor["amount"] = quantize_money(
            debtor["amount"]
        )
        creditor["amount"] = quantize_money(
            creditor["amount"]
        )

        if debtor["amount"] == 0:
            debtor_index += 1

        if creditor["amount"] == 0:
            creditor_index += 1

    return settlements


def calculate_expense_summary(
    expenses,
    money_transfers=None,
):
    """
    Calculate all financial information.

    Money Transfers affect final net balances and settlements.

    Money Transfers do NOT affect:
        - total_expenses
        - total_paid
        - expense_shares

    Args:
        expenses: A list of Expense dictionaries.
        money_transfers: Optional list of Money Transfer
                         dictionaries.

    Returns:
        dict containing:
            - total_expenses
            - total_paid
            - expense_shares
            - net_balances
            - settlements
            - everyone_settled
    """
    if money_transfers is None:
        money_transfers = []

    total_expenses = Decimal("0")

    total_paid = {
        user: Decimal("0")
        for user in USERS
    }

    expense_shares = []

    expense_net_balances = {
        user: Decimal("0")
        for user in USERS
    }

    for expense in expenses:
        amount = to_decimal(expense["amount"])

        shares = calculate_expense_shares(
            expense
        )

        expense_shares.append(
            {
                "id": expense.get("id"),
                "shares": shares,
            }
        )

        total_expenses += amount

        payer = expense["paid_by"]

        if payer not in USERS:
            raise ValueError(
                "Invalid expense payer."
            )

        total_paid[payer] += amount

        for user in USERS:
            expense_net_balances[user] -= (
                shares[user]
            )

        expense_net_balances[payer] += amount

    net_balances = apply_money_transfers(
        expense_net_balances,
        money_transfers,
    )

    total_expenses = quantize_money(
        total_expenses
    )

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

    settlements = calculate_settlement(
        net_balances
    )

    everyone_settled = len(settlements) == 0

    return {
        "total_expenses": total_expenses,
        "total_paid": total_paid,
        "expense_shares": expense_shares,
        "net_balances": net_balances,
        "settlements": settlements,
        "everyone_settled": everyone_settled,
    }