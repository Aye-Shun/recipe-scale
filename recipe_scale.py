"""Scale the quantities in a recipe CSV."""

import argparse
import csv
import io
import re
import sys
from fractions import Fraction
from pathlib import Path

MAX_FILE_BYTES = 64 * 1024
MAX_QUANTITY_LENGTH = 32
MAX_SERVINGS = 10_000
SIMPLE_QUANTITY = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+|[0-9]+/[0-9]+)")
MIXED_QUANTITY = re.compile(r"([0-9]+) +([0-9]+)/([0-9]+)")


def parse_quantity(text: str) -> Fraction:
    if len(text) > MAX_QUANTITY_LENGTH:
        raise ValueError(f"quantity must be at most {MAX_QUANTITY_LENGTH} characters")

    mixed = MIXED_QUANTITY.fullmatch(text)
    if mixed:
        whole, numerator, denominator = map(int, mixed.groups())
        if not 0 < numerator < denominator:
            raise ValueError("mixed quantities require a proper fraction")
        quantity = whole + Fraction(numerator, denominator)
    elif SIMPLE_QUANTITY.fullmatch(text):
        try:
            quantity = Fraction(text)
        except ZeroDivisionError:
            raise ValueError("a fraction denominator cannot be zero") from None
    else:
        raise ValueError("expected a whole number, decimal, fraction, or mixed number")
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")
    return quantity


def format_quantity(quantity: Fraction) -> str:
    whole, remainder = divmod(quantity.numerator, quantity.denominator)
    if not remainder:
        return str(whole)
    part = f"{remainder}/{quantity.denominator}"
    return f"{whole} {part}" if whole else part


def read_recipe(path: Path) -> list[tuple[Fraction, str, str]]:
    with path.open("rb") as recipe:
        data = recipe.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("recipe must be at most 64 KiB")
    try:
        contents = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("recipe must be UTF-8") from None

    reader = csv.reader(io.StringIO(contents, newline=""), strict=True)
    ingredients = []
    try:
        if next(reader, None) != ["quantity", "unit", "ingredient"]:
            raise ValueError("expected a quantity,unit,ingredient header")
        for row in reader:
            if not row:
                continue
            if len(row) != 3:
                raise ValueError(f"line {reader.line_num}: expected three columns")
            amount, unit, ingredient = (field.strip() for field in row)
            if not ingredient or not ingredient.isprintable() or (unit and not unit.isprintable()):
                raise ValueError(f"line {reader.line_num}: use a single-line ingredient and unit")
            try:
                quantity = parse_quantity(amount)
            except ValueError as error:
                raise ValueError(f"line {reader.line_num}: {error}") from None
            ingredients.append((quantity, unit, ingredient))
    except csv.Error as error:
        raise ValueError(f"line {reader.line_num}: invalid CSV ({error})") from None
    if not ingredients:
        raise ValueError("recipe has no ingredients")
    return ingredients


def serving_count(text: str) -> int:
    if re.fullmatch(r"[0-9]{1,5}", text) and 1 <= int(text) <= MAX_SERVINGS:
        return int(text)
    raise argparse.ArgumentTypeError(f"servings must be a whole number from 1 to {MAX_SERVINGS:,}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path, help="UTF-8 recipe CSV")
    parser.add_argument("--from", dest="original", type=serving_count, required=True,
                        help="original servings")
    parser.add_argument("--to", dest="target", type=serving_count, required=True,
                        help="target servings")
    args = parser.parse_args()
    try:
        ingredients = read_recipe(args.recipe)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{parser.prog}: {error}\n")

    ratio = Fraction(args.target, args.original)
    print(f"{args.original} to {args.target} servings")
    for quantity, unit, ingredient in ingredients:
        parts = (format_quantity(quantity * ratio), unit, ingredient)
        print(" ".join(part for part in parts if part))
    return 0


if __name__ == "__main__":
    sys.exit(main())
