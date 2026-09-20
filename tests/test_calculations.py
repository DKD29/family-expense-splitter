from decimal import Decimal

import pytest

from calculations import (
    to_decimal,
    quantize_money,
    calculate_expense_shares,
    calculate_totals,
    calculate_net_balances,
    calculate_settlement,
    calculate_expense_summary,
)


def expense(
    amount,
    paid_by,
    krishna_ratio=1,
    karthik_ratio=1,
    krishnamurty_ratio=1,
    expense_id=None,
):
    """Create a test Expense dictionary."""
    return {
        "id": expense_id,
        "amount": amount,
        "paid_by": paid_by,
        "krishna_ratio": krishna_ratio,
        "karthik_ratio": karthik_ratio,
        "krishnamurty_ratio": krishnamurty_ratio,
    }


# ============================================================
# to_decimal()
# ============================================================

def test_to_decimal_accepts_integer():
    assert to_decimal(100) == Decimal("100")


def test_to_decimal_accepts_decimal():
    value = Decimal("100.50")
    assert to_decimal(value) == Decimal("100.50")


def test_to_decimal_accepts_finite_float():
    assert to_decimal(100.5) == Decimal("100.5")


def test_to_decimal_rejects_nan():
    with pytest.raises(ValueError):
        to_decimal(float("nan"))


def test_to_decimal_rejects_positive_infinity():
    with pytest.raises(ValueError):
        to_decimal(float("inf"))


def test_to_decimal_rejects_negative_infinity():
    with pytest.raises(ValueError):
        to_decimal(float("-inf"))


def test_to_decimal_rejects_invalid_text():
    with pytest.raises(ValueError):
        to_decimal("not a number")


# ============================================================
# quantize_money()
# ============================================================

def test_quantize_money_rounds_to_two_decimal_places():
    assert quantize_money(Decimal("100.123")) == Decimal("100.12")


def test_quantize_money_preserves_two_decimal_places():
    assert quantize_money(Decimal("100.50")) == Decimal("100.50")


# ============================================================
# calculate_expense_shares()
# ============================================================

def test_equal_expense_split():
    result = calculate_expense_shares(
        expense(900, "Krishna", 1, 1, 1)
    )

    assert result["Krishna"] == Decimal("300")
    assert result["Karthik"] == Decimal("300")
    assert result["Krishnamurty"] == Decimal("300")


def test_custom_ratio_split():
    result = calculate_expense_shares(
        expense(900, "Krishna", 2, 1, 0)
    )

    assert result["Krishna"] == Decimal("600")
    assert result["Karthik"] == Decimal("300")
    assert result["Krishnamurty"] == Decimal("0")


def test_decimal_ratios():
    result = calculate_expense_shares(
        expense(1000, "Krishna", 1.5, 1, 1)
    )

    assert result["Krishna"] == Decimal("1000") * Decimal("1.5") / Decimal("3.5")
    assert result["Karthik"] == Decimal("1000") / Decimal("3.5")
    assert result["Krishnamurty"] == Decimal("1000") / Decimal("3.5")


def test_zero_ratio_for_one_user():
    result = calculate_expense_shares(
        expense(1000, "Krishna", 1, 1, 0)
    )

    assert result["Krishnamurty"] == Decimal("0")
    assert result["Krishna"] == Decimal("500")
    assert result["Karthik"] == Decimal("500")


def test_one_user_responsible_for_100_percent():
    result = calculate_expense_shares(
        expense(1000, "Karthik", 0, 1, 0)
    )

    assert result["Krishna"] == Decimal("0")
    assert result["Karthik"] == Decimal("1000")
    assert result["Krishnamurty"] == Decimal("0")


def test_very_large_ratio():
    result = calculate_expense_shares(
        expense(1000, "Krishna", 100, 1, 1)
    )

    assert result["Krishna"] == Decimal("100000") / Decimal("102")
    assert result["Karthik"] == Decimal("1000") / Decimal("102")
    assert result["Krishnamurty"] == Decimal("1000") / Decimal("102")


def test_zero_total_ratio_is_rejected():
    with pytest.raises(ValueError):
        calculate_expense_shares(
            expense(1000, "Krishna", 0, 0, 0)
        )


# ============================================================
# calculate_totals()
# ============================================================

def test_single_equal_expense_totals():
    expenses = [
        expense(900, "Krishna", 1, 1, 1)
    ]

    result = calculate_totals(expenses)

    assert result["total_expenses"] == Decimal("900")

    assert result["total_paid"] == {
        "Krishna": Decimal("900"),
        "Krishnamurty": Decimal("0"),
        "Karthik": Decimal("0"),
    }

    assert result["total_responsibility"] == {
        "Krishna": Decimal("300"),
        "Krishnamurty": Decimal("300"),
        "Karthik": Decimal("300"),
    }


def test_multiple_expenses_combine_correctly():
    expenses = [
        expense(900, "Krishna", 1, 1, 1),
        expense(600, "Karthik", 1, 1, 1),
    ]

    result = calculate_totals(expenses)

    assert result["total_expenses"] == Decimal("1500")

    assert result["total_paid"] == {
        "Krishna": Decimal("900"),
        "Krishnamurty": Decimal("0"),
        "Karthik": Decimal("600"),
    }

    assert result["total_responsibility"] == {
        "Krishna": Decimal("500"),
        "Krishnamurty": Decimal("500"),
        "Karthik": Decimal("500"),
    }


def test_payer_is_independent_from_ratio():
    expenses = [
        expense(900, "Karthik", 2, 1, 0)
    ]

    result = calculate_totals(expenses)

    assert result["total_paid"]["Karthik"] == Decimal("900")

    assert result["total_responsibility"]["Krishna"] == Decimal("600")
    assert result["total_responsibility"]["Karthik"] == Decimal("300")
    assert result["total_responsibility"]["Krishnamurty"] == Decimal("0")


def test_someone_pays_another_persons_entire_share():
    expenses = [
        expense(900, "Krishna", 0, 1, 0)
    ]

    result = calculate_totals(expenses)

    assert result["total_paid"]["Krishna"] == Decimal("900")
    assert result["total_responsibility"]["Karthik"] == Decimal("900")
    assert result["total_responsibility"]["Krishna"] == Decimal("0")
    assert result["total_responsibility"]["Krishnamurty"] == Decimal("0")


def test_expense_deletion_is_represented_by_removing_record():
    expenses = [
        expense(900, "Krishna", 1, 1, 1),
        expense(600, "Karthik", 1, 1, 1),
    ]

    before = calculate_totals(expenses)

    remaining_expenses = expenses[:1]

    after = calculate_totals(remaining_expenses)

    assert before["total_expenses"] == Decimal("1500")
    assert after["total_expenses"] == Decimal("900")

    assert after["total_paid"]["Krishna"] == Decimal("900")
    assert after["total_paid"]["Karthik"] == Decimal("0")


# ============================================================
# calculate_net_balances()
# ============================================================

def test_someone_pays_their_own_share():
    expenses = [
        expense(900, "Krishna", 1, 1, 1)
    ]

    result = calculate_net_balances(expenses)

    assert result["Krishna"] == Decimal("600")
    assert result["Karthik"] == Decimal("-300")
    assert result["Krishnamurty"] == Decimal("-300")


def test_multiple_creditors_and_one_debtor():
    expenses = [
        expense(1000, "Krishna", 1, 1, 1),
        expense(600, "Karthik", 1, 1, 1),
    ]

    result = calculate_net_balances(expenses)

    assert result["Krishna"] == Decimal("466.6666666666666666666666667")
    assert result["Krishnamurty"] == Decimal("-533.3333333333333333333333333")
    assert result["Karthik"] == Decimal("66.6666666666666666666666667")


def test_balances_sum_to_zero():
    expenses = [
        expense(1000, "Krishna", 1, 1, 1),
        expense(700, "Karthik", 2, 1, 1),
        expense(250, "Krishnamurty", 0, 1, 1),
    ]

    result = calculate_net_balances(expenses)

    assert abs(sum(result.values())) < Decimal("0.01")


# ============================================================
# calculate_settlement()
# ============================================================

def test_everyone_settled():
    balances = {
        "Krishna": Decimal("0"),
        "Krishnamurty": Decimal("0"),
        "Karthik": Decimal("0"),
    }

    assert calculate_settlement(balances) == []


def test_one_debtor_one_creditor():
    balances = {
        "Krishna": Decimal("500"),
        "Krishnamurty": Decimal("-500"),
        "Karthik": Decimal("0"),
    }

    result = calculate_settlement(balances)

    assert result == [
        {
            "from_user": "Krishnamurty",
            "to_user": "Krishna",
            "amount": Decimal("500.00"),
        }
    ]


def test_one_debtor_two_creditors():
    balances = {
        "Krishna": Decimal("500"),
        "Krishnamurty": Decimal("-700"),
        "Karthik": Decimal("200"),
    }

    result = calculate_settlement(balances)

    assert result == [
        {
            "from_user": "Krishnamurty",
            "to_user": "Krishna",
            "amount": Decimal("500.00"),
        },
        {
            "from_user": "Krishnamurty",
            "to_user": "Karthik",
            "amount": Decimal("200.00"),
        },
    ]


def test_two_debtors_one_creditor():
    balances = {
        "Krishna": Decimal("700"),
        "Krishnamurty": Decimal("-500"),
        "Karthik": Decimal("-200"),
    }

    result = calculate_settlement(balances)

    assert result == [
        {
            "from_user": "Krishnamurty",
            "to_user": "Krishna",
            "amount": Decimal("500.00"),
        },
        {
            "from_user": "Karthik",
            "to_user": "Krishna",
            "amount": Decimal("200.00"),
        },
    ]


def test_settlement_simplifies_underlying_expenses():
    balances = {
        "Krishna": Decimal("500"),
        "Krishnamurty": Decimal("-700"),
        "Karthik": Decimal("200"),
    }

    result = calculate_settlement(balances)

    assert len(result) == 2

    assert result[0]["from_user"] == "Krishnamurty"
    assert result[0]["to_user"] == "Krishna"

    assert result[1]["from_user"] == "Krishnamurty"
    assert result[1]["to_user"] == "Karthik"


def test_settlement_amounts_are_two_decimal_places():
    balances = {
        "Krishna": Decimal("333.333"),
        "Krishnamurty": Decimal("-333.333"),
        "Karthik": Decimal("0"),
    }

    result = calculate_settlement(balances)

    assert result[0]["amount"] == Decimal("333.33")


# ============================================================
# Rounding cases
# ============================================================

def test_one_hundred_divided_by_three():
    result = calculate_expense_shares(
        expense(100, "Krishna", 1, 1, 1)
    )

    assert result["Krishna"] == Decimal("100") / Decimal("3")
    assert result["Karthik"] == Decimal("100") / Decimal("3")
    assert result["Krishnamurty"] == Decimal("100") / Decimal("3")


def test_one_divided_by_three():
    result = calculate_expense_shares(
        expense(1, "Krishna", 1, 1, 1)
    )

    assert result["Krishna"] == Decimal("1") / Decimal("3")
    assert result["Karthik"] == Decimal("1") / Decimal("3")
    assert result["Krishnamurty"] == Decimal("1") / Decimal("3")


def test_one_hundred_point_fifty_divided_by_three():
    result = calculate_expense_shares(
        expense(Decimal("100.50"), "Krishna", 1, 1, 1)
    )

    expected = Decimal("100.50") / Decimal("3")

    assert result["Krishna"] == expected
    assert result["Karthik"] == expected
    assert result["Krishnamurty"] == expected


# ============================================================
# calculate_expense_summary()
# ============================================================

def test_expense_summary_contains_all_required_fields():
    expenses = [
        expense(
            900,
            "Krishna",
            1,
            1,
            1,
            expense_id="expense-1",
        )
    ]

    result = calculate_expense_summary(expenses)

    assert set(result.keys()) == {
        "total_expenses",
        "total_paid",
        "expense_shares",
        "net_balances",
        "settlements",
        "everyone_settled",
    }


def test_expense_summary_equal_split():
    expenses = [
        expense(
            900,
            "Krishna",
            1,
            1,
            1,
            expense_id="expense-1",
        )
    ]

    result = calculate_expense_summary(expenses)

    assert result["total_expenses"] == Decimal("900")

    assert result["total_paid"] == {
        "Krishna": Decimal("900.00"),
        "Krishnamurty": Decimal("0.00"),
        "Karthik": Decimal("0.00"),
    }

    assert result["expense_shares"] == [
        {
            "id": "expense-1",
            "shares": {
                "Krishna": Decimal("300.00"),
                "Karthik": Decimal("300.00"),
                "Krishnamurty": Decimal("300.00"),
            },
        }
    ]

    assert result["net_balances"] == {
        "Krishna": Decimal("600.00"),
        "Krishnamurty": Decimal("-300.00"),
        "Karthik": Decimal("-300.00"),
    }

    assert result["everyone_settled"] is False


def test_expense_summary_everyone_settled():
    expenses = [
        expense(
            900,
            "Krishna",
            1,
            0,
            0,
            expense_id="expense-1",
        ),
        expense(
            900,
            "Karthik",
            0,
            1,
            0,
            expense_id="expense-2",
        ),
        expense(
            900,
            "Krishnamurty",
            0,
            0,
            1,
            expense_id="expense-3",
        ),
    ]

    result = calculate_expense_summary(expenses)

    assert result["total_expenses"] == Decimal("2700.00")

    assert result["net_balances"] == {
        "Krishna": Decimal("0.00"),
        "Krishnamurty": Decimal("0.00"),
        "Karthik": Decimal("0.00"),
    }

    assert result["settlements"] == []
    assert result["everyone_settled"] is True


def test_expense_summary_multiple_expenses_cancel_out():
    expenses = [
        expense(
            900,
            "Krishna",
            1,
            1,
            1,
            expense_id="expense-1",
        ),
        expense(
            900,
            "Karthik",
            1,
            1,
            1,
            expense_id="expense-2",
        ),
        expense(
            900,
            "Krishnamurty",
            1,
            1,
            1,
            expense_id="expense-3",
        ),
    ]

    result = calculate_expense_summary(expenses)

    assert result["total_expenses"] == Decimal("2700.00")

    assert result["net_balances"] == {
        "Krishna": Decimal("0.00"),
        "Krishnamurty": Decimal("0.00"),
        "Karthik": Decimal("0.00"),
    }

    assert result["settlements"] == []
    assert result["everyone_settled"] is True


def test_expense_summary_after_expense_deletion():
    expenses = [
        expense(
            900,
            "Krishna",
            1,
            1,
            1,
            expense_id="expense-1",
        ),
        expense(
            600,
            "Karthik",
            1,
            1,
            1,
            expense_id="expense-2",
        ),
    ]

    before = calculate_expense_summary(expenses)

    remaining_expenses = [
        expenses[0]
    ]

    after = calculate_expense_summary(remaining_expenses)

    assert before["total_expenses"] == Decimal("1500.00")
    assert after["total_expenses"] == Decimal("900.00")

    assert after["total_paid"]["Krishna"] == Decimal("900.00")
    assert after["total_paid"]["Karthik"] == Decimal("0.00")

    assert after["expense_shares"] == [
        {
            "id": "expense-1",
            "shares": {
                "Krishna": Decimal("300.00"),
                "Karthik": Decimal("300.00"),
                "Krishnamurty": Decimal("300.00"),
            },
        }
    ]


def test_expense_summary_very_large_ratio():
    expenses = [
        expense(
            1000,
            "Karthik",
            100,
            1,
            1,
            expense_id="large-ratio",
        )
    ]

    result = calculate_expense_summary(expenses)

    assert result["total_expenses"] == Decimal("1000.00")
    assert result["total_paid"]["Karthik"] == Decimal("1000.00")

    assert result["expense_shares"][0]["shares"]["Krishna"] == Decimal("980.39")
    assert result["expense_shares"][0]["shares"]["Karthik"] == Decimal("9.80")
    assert result["expense_shares"][0]["shares"]["Krishnamurty"] == Decimal("9.80")


def test_expense_summary_rounds_final_values_to_two_decimal_places():
    expenses = [
        expense(
            Decimal("100.50"),
            "Krishna",
            1,
            1,
            1,
            expense_id="rounding-test",
        )
    ]

    result = calculate_expense_summary(expenses)

    shares = result["expense_shares"][0]["shares"]

    assert shares["Krishna"] == Decimal("33.50")
    assert shares["Karthik"] == Decimal("33.50")
    assert shares["Krishnamurty"] == Decimal("33.50")


# ============================================================
# Money Transfer isolation
# ============================================================

def test_calculation_engine_requires_only_expenses():
    """
    Money Transfers are deliberately not part of the calculation API.

    This verifies that the calculation engine operates entirely from
    Expense records and does not require a Money Transfer collection.
    """
    expenses = [
        expense(900, "Krishna", 1, 1, 1)
    ]

    result = calculate_expense_summary(expenses)

    assert result["total_expenses"] == Decimal("900.00")
    assert result["total_paid"]["Krishna"] == Decimal("900.00")


# ============================================================
# Empty expense list
# ============================================================

def test_empty_expense_list():
    result = calculate_expense_summary([])

    assert result["total_expenses"] == Decimal("0.00")

    assert result["total_paid"] == {
        "Krishna": Decimal("0.00"),
        "Krishnamurty": Decimal("0.00"),
        "Karthik": Decimal("0.00"),
    }

    assert result["expense_shares"] == []

    assert result["net_balances"] == {
        "Krishna": Decimal("0.00"),
        "Krishnamurty": Decimal("0.00"),
        "Karthik": Decimal("0.00"),
    }

    assert result["settlements"] == []
    assert result["everyone_settled"] is True