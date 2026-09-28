from domain import MENU, PHRASES, load_json

SAY = PHRASES["lookups"]
NUMBER_WORDS = PHRASES["spoken_numbers"]
NEEDS_CONFIRMATION = {"lock_card"}
DEFAULT_AFTER_DIALING = MENU["default_after_dialing"]

customers = load_json("customers.json")


def reset_customers():
    global customers
    customers = load_json("customers.json")


def spell_amount(amount):
    millions, rest = divmod(amount, 1_000_000)
    thousands = rest // 1_000
    parts = []
    if millions:
        parts.append(f"{millions} {NUMBER_WORDS['million']}")
    if thousands or not millions:
        parts.append(f"{thousands} {NUMBER_WORDS['thousand']}")
    return " ".join(parts) + f" {NUMBER_WORDS['currency']}"


def spell_date(day_and_month):
    day, month = day_and_month.split("/")
    return f"{int(day)} {NUMBER_WORDS['month']} {int(month)}"


def check_balance(customer):
    return SAY["check_balance"].format(balance=spell_amount(customer["balance"]))


def last_transaction(customer):
    if not customer["transactions"]:
        return SAY["no_transactions"]
    latest = customer["transactions"][0]
    return SAY["last_transaction"].format(date=spell_date(latest["date"]), kind=latest["kind"],
                                          amount=spell_amount(latest["amount"]),
                                          counterparty=latest["counterparty"])


def daily_limit(customer):
    return SAY["daily_limit"].format(limit=spell_amount(customer["daily_limit"]))


def lock_card(customer):
    if customer["card_locked"]:
        return SAY["card_already_locked"]
    customer["card_locked"] = True
    return SAY["card_locked"]


LOOKUPS = {
    "check_balance": check_balance,
    "last_transaction": last_transaction,
    "daily_limit": daily_limit,
    "lock_card": lock_card,
}


def needs_confirmation(lookup):
    return lookup in NEEDS_CONFIRMATION


def run_lookup(lookup, phone_number):
    customer = customers.get("".join(c for c in phone_number if c.isdigit()))
    return LOOKUPS[lookup](customer) if customer else SAY["customer_not_found"]
