import csv
import io
import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP


mcp = FastMCP("FinMCP - AI Financial Operations")

DATABASE_PATH = Path(
    os.getenv(
        "FINMCP_DATABASE_PATH",
        str(Path(__file__).resolve().parents[2] / "finmcp.db"),
    )
)

DEFAULT_CURRENCY = os.getenv("FINMCP_CURRENCY", "INR")


# ============================================================
# DATABASE
# ============================================================

def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    _create_tables(connection)

    return connection


def _create_tables(connection: sqlite3.Connection):

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            account_type TEXT NOT NULL DEFAULT 'cash',
            currency TEXT NOT NULL DEFAULT 'INR',
            opening_balance REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            type TEXT NOT NULL
                CHECK(type IN ('income', 'expense', 'transfer')),

            description TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount >= 0),

            currency TEXT NOT NULL DEFAULT 'INR',

            category TEXT NOT NULL DEFAULT 'Other',
            subcategory TEXT NOT NULL DEFAULT '',

            merchant TEXT NOT NULL DEFAULT '',

            account_id INTEGER,

            transaction_date TEXT NOT NULL,

            notes TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY(account_id)
                REFERENCES accounts(id)
                ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            category TEXT NOT NULL,

            amount REAL NOT NULL CHECK(amount >= 0),

            month TEXT NOT NULL,

            currency TEXT NOT NULL DEFAULT 'INR',

            created_at TEXT NOT NULL,

            UNIQUE(category, month)
        );

        CREATE TABLE IF NOT EXISTS financial_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            target_amount REAL NOT NULL CHECK(target_amount > 0),

            current_amount REAL NOT NULL DEFAULT 0,

            target_date TEXT,

            currency TEXT NOT NULL DEFAULT 'INR',

            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recurring_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            description TEXT NOT NULL,

            amount REAL NOT NULL CHECK(amount >= 0),

            type TEXT NOT NULL
                CHECK(type IN ('income', 'expense')),

            category TEXT NOT NULL DEFAULT 'Other',

            frequency TEXT NOT NULL
                CHECK(frequency IN ('weekly', 'monthly', 'yearly')),

            next_due_date TEXT NOT NULL,

            active INTEGER NOT NULL DEFAULT 1,

            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            action TEXT NOT NULL,

            entity_type TEXT NOT NULL,

            entity_id INTEGER,

            details TEXT NOT NULL DEFAULT '',

            created_at TEXT NOT NULL
        );
        """
    )

    connection.commit()


# ============================================================
# HELPERS
# ============================================================

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _validate_date(value: str, field_name: str) -> str:

    try:
        return date.fromisoformat(value).isoformat()

    except ValueError as error:
        raise ValueError(
            f"{field_name} must use YYYY-MM-DD format"
        ) from error


def _validate_amount(amount: float) -> float:

    if amount < 0:
        raise ValueError("amount must be zero or greater")

    return round(float(amount), 2)


def _rows_to_json(rows) -> str:

    return json.dumps(
        [dict(row) for row in rows],
        indent=2,
        default=str
    )


def _log(
    connection,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: str = "",
):

    connection.execute(
        """
        INSERT INTO audit_logs
        (action, entity_type, entity_id, details, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            action,
            entity_type,
            entity_id,
            details,
            _now(),
        ),
    )


# ============================================================
# ACCOUNT TOOLS
# ============================================================

@mcp.tool
def create_account(
    name: str,
    account_type: str = "cash",
    currency: str = DEFAULT_CURRENCY,
    opening_balance: float = 0,
) -> str:
    """
    Create a financial account such as cash, bank, savings,
    credit card, wallet, or investment account.
    """

    name = name.strip()

    if not name:
        raise ValueError("account name cannot be empty")

    opening_balance = float(opening_balance)

    with _connect() as connection:

        cursor = connection.execute(
            """
            INSERT INTO accounts
            (name, account_type, currency, opening_balance, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                account_type.strip(),
                currency.upper(),
                opening_balance,
                _now(),
            ),
        )

        account_id = cursor.lastrowid

        _log(
            connection,
            "create",
            "account",
            account_id,
            name,
        )

    return f"Created account #{account_id}: {name}"


@mcp.tool
def list_accounts() -> str:
    """List all financial accounts."""

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM accounts
            ORDER BY id
            """
        ).fetchall()

    return _rows_to_json(rows)


# ============================================================
# TRANSACTION TOOLS
# ============================================================

@mcp.tool
def add_transaction(
    transaction_type: Literal["income", "expense", "transfer"],
    description: str,
    amount: float,
    category: str = "Other",
    transaction_date: str = "",
    account_id: int | None = None,
    currency: str = DEFAULT_CURRENCY,
    merchant: str = "",
    subcategory: str = "",
    notes: str = "",
    tags: str = "",
) -> str:
    """
    Add an income, expense, or transfer transaction.
    """

    description = description.strip()

    if not description:
        raise ValueError("description cannot be empty")

    amount = _validate_amount(amount)

    transaction_date = _validate_date(
        transaction_date or date.today().isoformat(),
        "transaction_date",
    )

    now = _now()

    with _connect() as connection:

        cursor = connection.execute(
            """
            INSERT INTO transactions
            (
                type,
                description,
                amount,
                currency,
                category,
                subcategory,
                merchant,
                account_id,
                transaction_date,
                notes,
                tags,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_type,
                description,
                amount,
                currency.upper(),
                category.strip() or "Other",
                subcategory.strip(),
                merchant.strip(),
                account_id,
                transaction_date,
                notes.strip(),
                tags.strip(),
                now,
                now,
            ),
        )

        transaction_id = cursor.lastrowid

        _log(
            connection,
            "create",
            "transaction",
            transaction_id,
            description,
        )

    return (
        f"Added {transaction_type} transaction "
        f"#{transaction_id}: "
        f"{description} "
        f"({currency.upper()} {amount:.2f})"
    )


@mcp.tool
def get_transaction(transaction_id: int) -> str:
    """Get one transaction by ID."""

    with _connect() as connection:

        row = connection.execute(
            """
            SELECT
                t.*,
                a.name AS account_name
            FROM transactions t
            LEFT JOIN accounts a
                ON t.account_id = a.id
            WHERE t.id = ?
            """,
            (transaction_id,),
        ).fetchone()

    if row is None:
        raise ValueError(
            f"transaction #{transaction_id} was not found"
        )

    return json.dumps(dict(row), indent=2)


@mcp.tool
def list_transactions(
    limit: int = 100,
    offset: int = 0,
    transaction_type: str = "",
    category: str = "",
) -> str:
    """
    List transactions with optional type/category filtering.
    """

    if limit < 1 or limit > 1000:
        raise ValueError("limit must be 1-1000")

    if offset < 0:
        raise ValueError("offset must be zero or greater")

    conditions = []
    params: list[Any] = []

    if transaction_type:
        conditions.append("t.type = ?")
        params.append(transaction_type)

    if category:
        conditions.append("LOWER(t.category) = LOWER(?)")
        params.append(category)

    where = ""

    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    params.extend([limit, offset])

    with _connect() as connection:

        rows = connection.execute(
            f"""
            SELECT
                t.*,
                a.name AS account_name
            FROM transactions t
            LEFT JOIN accounts a
                ON t.account_id = a.id
            {where}
            ORDER BY
                t.transaction_date DESC,
                t.id DESC
            LIMIT ?
            OFFSET ?
            """,
            params,
        ).fetchall()

    return _rows_to_json(rows)


@mcp.tool
def update_transaction(
    transaction_id: int,
    description: str = "",
    amount: float | None = None,
    category: str = "",
    transaction_date: str = "",
    merchant: str = "",
    notes: str | None = None,
    tags: str | None = None,
) -> str:
    """Update supplied fields of a transaction."""

    fields = {}

    if description:
        fields["description"] = description.strip()

    if amount is not None:
        fields["amount"] = _validate_amount(amount)

    if category:
        fields["category"] = category.strip()

    if transaction_date:
        fields["transaction_date"] = _validate_date(
            transaction_date,
            "transaction_date",
        )

    if merchant:
        fields["merchant"] = merchant.strip()

    if notes is not None:
        fields["notes"] = notes.strip()

    if tags is not None:
        fields["tags"] = tags.strip()

    if not fields:
        raise ValueError(
            "provide at least one field to update"
        )

    fields["updated_at"] = _now()

    assignments = ", ".join(
        f"{field} = ?"
        for field in fields
    )

    with _connect() as connection:

        cursor = connection.execute(
            f"""
            UPDATE transactions
            SET {assignments}
            WHERE id = ?
            """,
            (
                *fields.values(),
                transaction_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"transaction #{transaction_id} was not found"
            )

        _log(
            connection,
            "update",
            "transaction",
            transaction_id,
        )

    return f"Updated transaction #{transaction_id}"


@mcp.tool
def delete_transaction(transaction_id: int) -> str:
    """
    Delete a transaction.

    In a production deployment this operation should require
    explicit user confirmation.
    """

    with _connect() as connection:

        cursor = connection.execute(
            """
            DELETE FROM transactions
            WHERE id = ?
            """,
            (transaction_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"transaction #{transaction_id} was not found"
            )

        _log(
            connection,
            "delete",
            "transaction",
            transaction_id,
        )

    return f"Deleted transaction #{transaction_id}"


# ============================================================
# SEARCH
# ============================================================

@mcp.tool
def search_transactions(
    query: str,
    limit: int = 100,
) -> str:
    """Search descriptions, categories, merchants and notes."""

    query = query.strip()

    if not query:
        raise ValueError("query cannot be empty")

    pattern = f"%{query}%"

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM transactions
            WHERE
                description LIKE ?
                OR category LIKE ?
                OR merchant LIKE ?
                OR notes LIKE ?
                OR tags LIKE ?
            ORDER BY
                transaction_date DESC,
                id DESC
            LIMIT ?
            """,
            (
                pattern,
                pattern,
                pattern,
                pattern,
                pattern,
                limit,
            ),
        ).fetchall()

    return _rows_to_json(rows)


# ============================================================
# FINANCIAL SUMMARY
# ============================================================

@mcp.tool
def get_spending_summary(
    start_date: str = "",
    end_date: str = "",
) -> str:
    """
    Calculate total expenses, average expense,
    minimum and maximum expense.
    """

    start_date = (
        _validate_date(start_date, "start_date")
        if start_date
        else "0001-01-01"
    )

    end_date = (
        _validate_date(end_date, "end_date")
        if end_date
        else "9999-12-31"
    )

    if start_date > end_date:
        raise ValueError(
            "start_date cannot be after end_date"
        )

    with _connect() as connection:

        row = connection.execute(
            """
            SELECT
                COUNT(*) AS transaction_count,
                COALESCE(SUM(amount), 0) AS total_spending,
                COALESCE(AVG(amount), 0) AS average_spending,
                COALESCE(MIN(amount), 0) AS minimum_spending,
                COALESCE(MAX(amount), 0) AS maximum_spending
            FROM transactions
            WHERE
                type = 'expense'
                AND transaction_date BETWEEN ? AND ?
            """,
            (
                start_date,
                end_date,
            ),
        ).fetchone()

    result = dict(row)

    result["currency"] = DEFAULT_CURRENCY
    result["start_date"] = start_date
    result["end_date"] = end_date

    return json.dumps(result, indent=2)


@mcp.tool
def get_category_breakdown(
    start_date: str = "",
    end_date: str = "",
) -> str:
    """Return expense totals grouped by category."""

    start_date = (
        _validate_date(start_date, "start_date")
        if start_date
        else "0001-01-01"
    )

    end_date = (
        _validate_date(end_date, "end_date")
        if end_date
        else "9999-12-31"
    )

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT
                category,
                COUNT(*) AS transaction_count,
                ROUND(SUM(amount), 2) AS total
            FROM transactions
            WHERE
                type = 'expense'
                AND transaction_date BETWEEN ? AND ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (
                start_date,
                end_date,
            ),
        ).fetchall()

    return _rows_to_json(rows)


@mcp.tool
def get_cash_flow(
    start_date: str = "",
    end_date: str = "",
) -> str:
    """Calculate income, expenses and net cash flow."""

    start_date = (
        _validate_date(start_date, "start_date")
        if start_date
        else "0001-01-01"
    )

    end_date = (
        _validate_date(end_date, "end_date")
        if end_date
        else "9999-12-31"
    )

    with _connect() as connection:

        row = connection.execute(
            """
            SELECT

                COALESCE(
                    SUM(
                        CASE
                            WHEN type = 'income'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_income,

                COALESCE(
                    SUM(
                        CASE
                            WHEN type = 'expense'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_expenses

            FROM transactions

            WHERE transaction_date
            BETWEEN ? AND ?
            """,
            (
                start_date,
                end_date,
            ),
        ).fetchone()

    result = dict(row)

    result["net_cash_flow"] = round(
        result["total_income"]
        - result["total_expenses"],
        2,
    )

    return json.dumps(result, indent=2)


# ============================================================
# MONTHLY TREND
# ============================================================

@mcp.tool
def get_monthly_trend(
    months: int = 6,
) -> str:
    """Return monthly income, expenses and net cash flow."""

    if months < 1 or months > 60:
        raise ValueError("months must be 1-60")

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT
                substr(transaction_date, 1, 7) AS month,

                ROUND(
                    SUM(
                        CASE
                            WHEN type = 'income'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    2
                ) AS income,

                ROUND(
                    SUM(
                        CASE
                            WHEN type = 'expense'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    2
                ) AS expenses

            FROM transactions

            GROUP BY month

            ORDER BY month DESC

            LIMIT ?
            """,
            (months,),
        ).fetchall()

    result = []

    for row in rows:

        item = dict(row)

        item["net"] = round(
            item["income"] - item["expenses"],
            2,
        )

        result.append(item)

    return json.dumps(
        result,
        indent=2,
    )


# ============================================================
# BUDGETS
# ============================================================

@mcp.tool
def create_budget(
    category: str,
    amount: float,
    month: str = "",
    currency: str = DEFAULT_CURRENCY,
) -> str:
    """Create or replace a monthly category budget."""

    amount = _validate_amount(amount)

    if not month:
        month = date.today().strftime("%Y-%m")

    if len(month) != 7:
        raise ValueError(
            "month must use YYYY-MM format"
        )

    with _connect() as connection:

        connection.execute(
            """
            INSERT INTO budgets
            (
                category,
                amount,
                month,
                currency,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(category, month)

            DO UPDATE SET
                amount = excluded.amount,
                currency = excluded.currency
            """,
            (
                category.strip(),
                amount,
                month,
                currency.upper(),
                _now(),
            ),
        )

    return (
        f"Budget set for {category} "
        f"at {currency.upper()} {amount:.2f} "
        f"for {month}"
    )


@mcp.tool
def get_budget_status(
    month: str = "",
) -> str:
    """Compare monthly budgets against actual spending."""

    if not month:
        month = date.today().strftime("%Y-%m")

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT
                b.category,
                b.amount AS budget,

                COALESCE(
                    SUM(t.amount),
                    0
                ) AS spent

            FROM budgets b

            LEFT JOIN transactions t
                ON LOWER(t.category)
                    = LOWER(b.category)

                AND t.type = 'expense'

                AND substr(
                    t.transaction_date,
                    1,
                    7
                ) = b.month

            WHERE b.month = ?

            GROUP BY
                b.category,
                b.amount
            """,
            (month,),
        ).fetchall()

    result = []

    for row in rows:

        item = dict(row)

        item["remaining"] = round(
            item["budget"] - item["spent"],
            2,
        )

        item["percentage_used"] = round(
            (
                item["spent"]
                / item["budget"]
                * 100
            )
            if item["budget"]
            else 0,
            2,
        )

        item["status"] = (
            "over_budget"
            if item["spent"] > item["budget"]
            else "within_budget"
        )

        result.append(item)

    return json.dumps(
        result,
        indent=2,
    )


# ============================================================
# FINANCIAL GOALS
# ============================================================

@mcp.tool
def create_financial_goal(
    name: str,
    target_amount: float,
    target_date: str = "",
    currency: str = DEFAULT_CURRENCY,
) -> str:
    """Create a savings or financial goal."""

    target_amount = _validate_amount(target_amount)

    if target_amount <= 0:
        raise ValueError(
            "target_amount must be greater than zero"
        )

    if target_date:
        target_date = _validate_date(
            target_date,
            "target_date",
        )

    with _connect() as connection:

        cursor = connection.execute(
            """
            INSERT INTO financial_goals
            (
                name,
                target_amount,
                target_date,
                currency,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                target_amount,
                target_date or None,
                currency.upper(),
                _now(),
            ),
        )

        goal_id = cursor.lastrowid

    return f"Created financial goal #{goal_id}: {name}"


@mcp.tool
def contribute_to_goal(
    goal_id: int,
    amount: float,
) -> str:
    """Add money toward a financial goal."""

    amount = _validate_amount(amount)

    with _connect() as connection:

        cursor = connection.execute(
            """
            UPDATE financial_goals

            SET current_amount =
                current_amount + ?

            WHERE id = ?
            """,
            (
                amount,
                goal_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"goal #{goal_id} was not found"
            )

    return (
        f"Added {DEFAULT_CURRENCY} "
        f"{amount:.2f} to goal #{goal_id}"
    )


@mcp.tool
def get_goal_progress() -> str:
    """Return progress for all financial goals."""

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM financial_goals
            ORDER BY target_date
            """
        ).fetchall()

    result = []

    for row in rows:

        item = dict(row)

        item["remaining"] = round(
            max(
                item["target_amount"]
                - item["current_amount"],
                0,
            ),
            2,
        )

        item["percentage_complete"] = round(
            (
                item["current_amount"]
                / item["target_amount"]
                * 100
            ),
            2,
        )

        result.append(item)

    return json.dumps(
        result,
        indent=2,
    )


# ============================================================
# RECURRING PAYMENTS
# ============================================================

@mcp.tool
def create_recurring_transaction(
    description: str,
    amount: float,
    transaction_type: Literal["income", "expense"],
    category: str = "Other",
    frequency: Literal[
        "weekly",
        "monthly",
        "yearly"
    ] = "monthly",
    next_due_date: str = "",
) -> str:
    """Create a recurring income or expense."""

    amount = _validate_amount(amount)

    next_due_date = _validate_date(
        next_due_date or date.today().isoformat(),
        "next_due_date",
    )

    with _connect() as connection:

        cursor = connection.execute(
            """
            INSERT INTO recurring_transactions
            (
                description,
                amount,
                type,
                category,
                frequency,
                next_due_date,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                description.strip(),
                amount,
                transaction_type,
                category.strip(),
                frequency,
                next_due_date,
                _now(),
            ),
        )

        recurring_id = cursor.lastrowid

    return (
        f"Created recurring transaction "
        f"#{recurring_id}"
    )


@mcp.tool
def get_upcoming_payments(
    days: int = 30,
) -> str:
    """List active recurring transactions due soon."""

    if days < 1 or days > 365:
        raise ValueError("days must be 1-365")

    end_date = (
        date.today()
        + timedelta(days=days)
    ).isoformat()

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM recurring_transactions

            WHERE active = 1

            AND next_due_date
                BETWEEN ? AND ?

            ORDER BY next_due_date
            """,
            (
                date.today().isoformat(),
                end_date,
            ),
        ).fetchall()

    return _rows_to_json(rows)


# ============================================================
# DUPLICATE DETECTION
# ============================================================

@mcp.tool
def detect_duplicate_transactions() -> str:
    """
    Find likely duplicate transactions based on
    date, amount, description and merchant.
    """

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT
                a.id AS transaction_a,
                b.id AS transaction_b,

                a.amount,
                a.transaction_date,

                a.description AS description_a,
                b.description AS description_b,

                a.merchant AS merchant_a,
                b.merchant AS merchant_b

            FROM transactions a

            JOIN transactions b

                ON a.id < b.id

                AND a.amount = b.amount

                AND a.transaction_date
                    = b.transaction_date

                AND LOWER(a.description)
                    = LOWER(b.description)

            ORDER BY
                a.transaction_date DESC
            """
        ).fetchall()

    return _rows_to_json(rows)


# ============================================================
# ANOMALY DETECTION
# ============================================================

@mcp.tool
def detect_spending_anomalies(
    minimum_transactions: int = 5,
) -> str:
    """
    Identify unusually large expenses using category averages.
    This is deterministic analysis, not financial advice.
    """

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT
                t.id,
                t.description,
                t.amount,
                t.category,
                t.transaction_date,

                AVG(c.amount) AS category_average

            FROM transactions t

            JOIN transactions c

                ON LOWER(c.category)
                    = LOWER(t.category)

                AND c.type = 'expense'

                AND c.id != t.id

            WHERE t.type = 'expense'

            GROUP BY t.id

            HAVING COUNT(c.id) >= ?

            ORDER BY
                t.amount DESC
            """,
            (
                minimum_transactions,
            ),
        ).fetchall()

    result = []

    for row in rows:

        item = dict(row)

        average = item["category_average"]

        if average and item["amount"] >= average * 2:

            item["anomaly_ratio"] = round(
                item["amount"] / average,
                2,
            )

            result.append(item)

    return json.dumps(
        result,
        indent=2,
    )


# ============================================================
# SAVINGS RATE
# ============================================================

@mcp.tool
def calculate_savings_rate(
    start_date: str = "",
    end_date: str = "",
) -> str:
    """Calculate income, expenses and savings rate."""

    cash_flow = json.loads(
        get_cash_flow(
            start_date,
            end_date,
        )
    )

    income = cash_flow["total_income"]
    expenses = cash_flow["total_expenses"]

    savings = income - expenses

    savings_rate = (
        savings / income * 100
        if income > 0
        else 0
    )

    return json.dumps(
        {
            "income": income,
            "expenses": expenses,
            "savings": round(savings, 2),
            "savings_rate_percent": round(
                savings_rate,
                2,
            ),
        },
        indent=2,
    )


# ============================================================
# CSV IMPORT
# ============================================================

@mcp.tool
def import_transactions_csv(
    csv_text: str,
) -> str:
    """
    Import transactions from CSV.

    Expected columns:
    type,description,amount,category,transaction_date,
    merchant,notes
    """

    reader = csv.DictReader(
        io.StringIO(csv_text)
    )

    imported = 0

    with _connect() as connection:

        for row in reader:

            transaction_type = (
                row.get("type", "expense")
                .strip()
                .lower()
            )

            if transaction_type not in {
                "income",
                "expense",
                "transfer",
            }:
                continue

            description = (
                row.get("description", "")
                .strip()
            )

            if not description:
                continue

            amount = _validate_amount(
                float(row.get("amount", 0))
            )

            transaction_date = _validate_date(
                row.get(
                    "transaction_date",
                    date.today().isoformat(),
                ),
                "transaction_date",
            )

            now = _now()

            connection.execute(
                """
                INSERT INTO transactions
                (
                    type,
                    description,
                    amount,
                    currency,
                    category,
                    merchant,
                    transaction_date,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction_type,
                    description,
                    amount,
                    DEFAULT_CURRENCY,
                    row.get(
                        "category",
                        "Other",
                    ),
                    row.get(
                        "merchant",
                        "",
                    ),
                    transaction_date,
                    row.get(
                        "notes",
                        "",
                    ),
                    now,
                    now,
                ),
            )

            imported += 1

    return (
        f"Imported {imported} transactions."
    )


# ============================================================
# CSV EXPORT
# ============================================================

@mcp.tool
def export_transactions_csv() -> str:
    """Export all transactions as CSV."""

    with _connect() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM transactions
            ORDER BY transaction_date, id
            """
        ).fetchall()

    output = io.StringIO()

    fieldnames = [
        "id",
        "type",
        "description",
        "amount",
        "currency",
        "category",
        "subcategory",
        "merchant",
        "account_id",
        "transaction_date",
        "notes",
        "tags",
        "created_at",
        "updated_at",
    ]

    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
    )

    writer.writeheader()

    for row in rows:
        writer.writerow(dict(row))

    return output.getvalue()


# ============================================================
# FINANCIAL SNAPSHOT
# ============================================================

@mcp.tool
def financial_snapshot() -> str:
    """
    Return a deterministic financial overview
    suitable for an AI financial assistant.
    """

    with _connect() as connection:

        income = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE type = 'income'
            """
        ).fetchone()[0]

        expenses = connection.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE type = 'expense'
            """
        ).fetchone()[0]

        transaction_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM transactions
            """
        ).fetchone()[0]

        accounts = connection.execute(
            """
            SELECT COUNT(*)
            FROM accounts
            """
        ).fetchone()[0]

        goals = connection.execute(
            """
            SELECT COUNT(*)
            FROM financial_goals
            """
        ).fetchone()[0]

    savings = income - expenses

    return json.dumps(
        {
            "currency": DEFAULT_CURRENCY,
            "total_income": round(income, 2),
            "total_expenses": round(expenses, 2),
            "net_cash_flow": round(savings, 2),
            "transaction_count": transaction_count,
            "account_count": accounts,
            "financial_goal_count": goals,
        },
        indent=2,
    )


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":
    mcp.run()