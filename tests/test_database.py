from datetime import date, timedelta

import pytest

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
# TEST HELPERS
# ============================================================

def create_test_expense(
    description="Phase 4 pytest expense",
    amount=100.00,
    paid_by="Krishna",
    krishna_ratio=1,
    karthik_ratio=1,
    krishnamurty_ratio=1,
):
    return add_expense(
        date=date.today(),
        description=description,
        amount=amount,
        paid_by=paid_by,
        krishna_ratio=krishna_ratio,
        karthik_ratio=karthik_ratio,
        krishnamurty_ratio=krishnamurty_ratio,
    )


def create_test_transfer(
    description="Phase 4 pytest transfer",
    amount=100.00,
    from_user="Krishna",
    to_user="Karthik",
):
    return add_money_transfer(
        date=date.today(),
        description=description,
        amount=amount,
        from_user=from_user,
        to_user=to_user,
    )


# ============================================================
# EXPENSE CRUD
# ============================================================

def test_create_expense():
    expense = create_test_expense()

    try:
        assert expense["id"]
        assert expense["date"] == date.today().isoformat()
        assert expense["description"] == "Phase 4 pytest expense"
        assert float(expense["amount"]) == 100.00
        assert expense["paid_by"] == "Krishna"
        assert float(expense["krishna_ratio"]) == 1
        assert float(expense["karthik_ratio"]) == 1
        assert float(expense["krishnamurty_ratio"]) == 1
        assert expense["created_at"]
    finally:
        delete_expense(expense["id"])


def test_get_expenses_returns_created_expense():
    expense = create_test_expense()

    try:
        expenses = get_expenses()

        assert any(
            existing["id"] == expense["id"]
            for existing in expenses
        )
    finally:
        delete_expense(expense["id"])


def test_get_expenses_empty_database():
    """
    This test cannot safely assume the real family database is empty.

    Therefore this test is intentionally omitted from the live Supabase
    suite. Empty-list behavior is covered by the database contract and
    should be tested separately against an isolated test database.
    """
    pass


def test_expense_update_keeps_same_id():
    expense = create_test_expense()

    try:
        original_id = expense["id"]

        updated = update_expense(
            expense_id=original_id,
            date=date.today(),
            description="Updated pytest expense",
            amount=250.00,
            paid_by="Karthik",
            krishna_ratio=2,
            karthik_ratio=1,
            krishnamurty_ratio=0,
        )

        assert updated["id"] == original_id
        assert updated["description"] == "Updated pytest expense"
        assert float(updated["amount"]) == 250.00
        assert updated["paid_by"] == "Karthik"
        assert float(updated["krishna_ratio"]) == 2
        assert float(updated["karthik_ratio"]) == 1
        assert float(updated["krishnamurty_ratio"]) == 0

        matching = [
            item for item in get_expenses()
            if item["id"] == original_id
        ]

        assert len(matching) == 1

    finally:
        delete_expense(original_id)


def test_expense_delete_removes_record():
    expense = create_test_expense()
    expense_id = expense["id"]

    delete_expense(expense_id)

    expenses = get_expenses()

    assert not any(
        existing["id"] == expense_id
        for existing in expenses
    )


# ============================================================
# EXPENSE VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "amount",
    [0, -1, -100],
)
def test_expense_invalid_amount(amount):
    with pytest.raises(ValueError):
        create_test_expense(amount=amount)


@pytest.mark.parametrize(
    "description",
    ["", "   ", "\t", "\n"],
)
def test_expense_invalid_description(description):
    with pytest.raises(ValueError):
        create_test_expense(description=description)


def test_expense_invalid_payer():
    with pytest.raises(ValueError):
        create_test_expense(paid_by="Someone Else")


@pytest.mark.parametrize(
    "ratios",
    [
        (-1, 1, 1),
        (1, -1, 1),
        (1, 1, -1),
    ],
)
def test_expense_negative_ratio(ratios):
    with pytest.raises(ValueError):
        create_test_expense(
            krishna_ratio=ratios[0],
            karthik_ratio=ratios[1],
            krishnamurty_ratio=ratios[2],
        )


def test_expense_all_zero_ratios():
    with pytest.raises(ValueError):
        create_test_expense(
            krishna_ratio=0,
            karthik_ratio=0,
            krishnamurty_ratio=0,
        )


def test_expense_future_date():
    with pytest.raises(ValueError):
        add_expense(
            date=date.today() + timedelta(days=1),
            description="Future pytest expense",
            amount=100,
            paid_by="Krishna",
            krishna_ratio=1,
            karthik_ratio=1,
            krishnamurty_ratio=1,
        )


@pytest.mark.parametrize(
    "ratios",
    [
        (0, 1, 1),
        (1, 0, 1),
        (1, 1, 0),
        (1.5, 1, 1),
        (100, 1, 1),
    ],
)
def test_expense_valid_ratio_edge_cases(ratios):
    expense = create_test_expense(
        krishna_ratio=ratios[0],
        karthik_ratio=ratios[1],
        krishnamurty_ratio=ratios[2],
    )

    try:
        assert float(expense["krishna_ratio"]) == ratios[0]
        assert float(expense["karthik_ratio"]) == ratios[1]
        assert float(expense["krishnamurty_ratio"]) == ratios[2]
    finally:
        delete_expense(expense["id"])


# ============================================================
# EXPENSE ORDERING
# ============================================================

def test_expenses_are_ordered_newest_first():
    older = add_expense(
        date=date.today() - timedelta(days=1),
        description="Older pytest expense",
        amount=100,
        paid_by="Krishna",
        krishna_ratio=1,
        karthik_ratio=1,
        krishnamurty_ratio=1,
    )

    newer = add_expense(
        date=date.today(),
        description="Newer pytest expense",
        amount=100,
        paid_by="Krishna",
        krishna_ratio=1,
        karthik_ratio=1,
        krishnamurty_ratio=1,
    )

    try:
        expenses = get_expenses()

        ids = [expense["id"] for expense in expenses]

        assert ids.index(newer["id"]) < ids.index(older["id"])

    finally:
        delete_expense(older["id"])
        delete_expense(newer["id"])


# ============================================================
# NONEXISTENT EXPENSE IDS
# ============================================================

def test_update_nonexistent_expense_fails():
    fake_id = "00000000-0000-0000-0000-000000000000"

    with pytest.raises(DatabaseError):
        update_expense(
            expense_id=fake_id,
            date=date.today(),
            description="Should fail",
            amount=100,
            paid_by="Krishna",
            krishna_ratio=1,
            karthik_ratio=1,
            krishnamurty_ratio=1,
        )


def test_delete_nonexistent_expense_fails():
    fake_id = "00000000-0000-0000-0000-000000000000"

    with pytest.raises(DatabaseError):
        delete_expense(fake_id)


# ============================================================
# MONEY TRANSFER CRUD
# ============================================================

def test_create_money_transfer():
    transfer = create_test_transfer()

    try:
        assert transfer["id"]
        assert transfer["date"] == date.today().isoformat()
        assert transfer["description"] == "Phase 4 pytest transfer"
        assert float(transfer["amount"]) == 100.00
        assert transfer["from_user"] == "Krishna"
        assert transfer["to_user"] == "Karthik"
        assert transfer["created_at"]
    finally:
        delete_money_transfer(transfer["id"])


def test_get_money_transfers_returns_created_transfer():
    transfer = create_test_transfer()

    try:
        transfers = get_money_transfers()

        assert any(
            existing["id"] == transfer["id"]
            for existing in transfers
        )
    finally:
        delete_money_transfer(transfer["id"])


def test_update_money_transfer_keeps_same_id():
    transfer = create_test_transfer()

    try:
        original_id = transfer["id"]

        updated = update_money_transfer(
            transfer_id=original_id,
            date=date.today(),
            description="Updated pytest transfer",
            amount=250.00,
            from_user="Karthik",
            to_user="Krishnamurty",
        )

        assert updated["id"] == original_id
        assert updated["description"] == "Updated pytest transfer"
        assert float(updated["amount"]) == 250.00
        assert updated["from_user"] == "Karthik"
        assert updated["to_user"] == "Krishnamurty"

        matching = [
            item for item in get_money_transfers()
            if item["id"] == original_id
        ]

        assert len(matching) == 1

    finally:
        delete_money_transfer(original_id)


def test_delete_money_transfer_removes_record():
    transfer = create_test_transfer()
    transfer_id = transfer["id"]

    delete_money_transfer(transfer_id)

    transfers = get_money_transfers()

    assert not any(
        existing["id"] == transfer_id
        for existing in transfers
    )


# ============================================================
# MONEY TRANSFER VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "amount",
    [0, -1, -100],
)
def test_money_transfer_invalid_amount(amount):
    with pytest.raises(ValueError):
        create_test_transfer(amount=amount)


@pytest.mark.parametrize(
    "description",
    ["", "   ", "\t", "\n"],
)
def test_money_transfer_invalid_description(description):
    with pytest.raises(ValueError):
        create_test_transfer(description=description)


def test_money_transfer_invalid_from_user():
    with pytest.raises(ValueError):
        create_test_transfer(from_user="Someone Else")


def test_money_transfer_invalid_to_user():
    with pytest.raises(ValueError):
        create_test_transfer(to_user="Someone Else")


def test_money_transfer_same_sender_and_receiver():
    with pytest.raises(ValueError):
        create_test_transfer(
            from_user="Krishna",
            to_user="Krishna",
        )


def test_money_transfer_future_date():
    with pytest.raises(ValueError):
        add_money_transfer(
            date=date.today() + timedelta(days=1),
            description="Future pytest transfer",
            amount=100,
            from_user="Krishna",
            to_user="Karthik",
        )


# ============================================================
# MONEY TRANSFER ORDERING
# ============================================================

def test_money_transfers_are_ordered_newest_first():
    older = add_money_transfer(
        date=date.today() - timedelta(days=1),
        description="Older pytest transfer",
        amount=100,
        from_user="Krishna",
        to_user="Karthik",
    )

    newer = add_money_transfer(
        date=date.today(),
        description="Newer pytest transfer",
        amount=100,
        from_user="Krishna",
        to_user="Karthik",
    )

    try:
        transfers = get_money_transfers()

        ids = [transfer["id"] for transfer in transfers]

        assert ids.index(newer["id"]) < ids.index(older["id"])

    finally:
        delete_money_transfer(older["id"])
        delete_money_transfer(newer["id"])


# ============================================================
# NONEXISTENT MONEY TRANSFER IDS
# ============================================================

def test_update_nonexistent_money_transfer_fails():
    fake_id = "00000000-0000-0000-0000-000000000000"

    with pytest.raises(DatabaseError):
        update_money_transfer(
            transfer_id=fake_id,
            date=date.today(),
            description="Should fail",
            amount=100,
            from_user="Krishna",
            to_user="Karthik",
        )


def test_delete_nonexistent_money_transfer_fails():
    fake_id = "00000000-0000-0000-0000-000000000000"

    with pytest.raises(DatabaseError):
        delete_money_transfer(fake_id)


# ============================================================
# EXPENSE / MONEY TRANSFER SEPARATION
# ============================================================

def test_money_transfer_does_not_appear_in_expenses():
    expense = create_test_expense()
    transfer = create_test_transfer()

    try:
        expenses = get_expenses()

        assert any(
            item["id"] == expense["id"]
            for item in expenses
        )

        assert not any(
            item["id"] == transfer["id"]
            for item in expenses
        )

    finally:
        delete_expense(expense["id"])
        delete_money_transfer(transfer["id"])


def test_expense_does_not_appear_in_money_transfers():
    expense = create_test_expense()
    transfer = create_test_transfer()

    try:
        transfers = get_money_transfers()

        assert any(
            item["id"] == transfer["id"]
            for item in transfers
        )

        assert not any(
            item["id"] == expense["id"]
            for item in transfers
        )

    finally:
        delete_expense(expense["id"])
        delete_money_transfer(transfer["id"])