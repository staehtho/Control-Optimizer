import re
from sympy import expand, Poly, symbols, factor, simplify, latex, sympify


def str2array(text: str) -> list[float]:
    """
    Parse a string of numbers into a list of floats.

    Accepts whitespace, comma, or semicolon separators and returns an empty list
    on invalid input.
    """
    if not text.strip():
        return []
    try:
        # Separators: whitespace, comma, semicolon.
        parts = re.split(r"[,\s;]+", text.strip())

        result = [float(p.replace(",", ".")) for p in parts if p]

        return result

    except ValueError:
        return []

def expr2array(expr: str) -> list[float]:
    """
    Convert a polynomial expression in s into its coefficient list.

    The expression is normalized to insert implicit multiplications and to
    convert '^' to '**' before expansion.
    """
    s = symbols('s')

    expr = _normalize_expr(expr)

    expanded = expand(expr)
    coefficients = Poly(expanded, s).all_coeffs()
    return [float(c) for c in coefficients]


def array2expr(coefficients: list[float]) -> str:
    """
    Convert a coefficient list into a factored polynomial expression string.

    Integer-like floats are rendered without a trailing '.0'.
    """
    s = symbols('s')

    # create polynomial
    poly = Poly(coefficients, s).as_expr()

    # factor polynomial
    factored = factor(poly)

    # get factors as a list
    factors = factored.as_ordered_factors()

    normalized_factors: list[str] = []
    final_gain = 1.0

    for f in factors:
        if f.is_Number:
            final_gain *= float(f)
        else:
            # factor out leading coefficient of s
            f_poly = Poly(f, s)
            lc = f_poly.LC()
            normalized = simplify(f / lc)

            # convert to string
            f_str = _strip_float_zeros(str(normalized))

            normalized_factors.append(f_str)

            # multiply the lc into the final gain
            final_gain *= lc

    normalized_factors = _clean_factors(normalized_factors)
    if len(normalized_factors) == 0:
        return _strip_float_zeros(f"{final_gain}")

    # format final gain
    if float(final_gain) == 1.0:
        gain_str = ''
    elif float(final_gain).is_integer():
        gain_str = str(int(final_gain)) + '*'
    else:
        gain_str = _strip_float_zeros(str(final_gain)) + '*'

    # join factors
    result = ''.join(normalized_factors)
    return f"{gain_str}{result}"


def expr2latex(expr: str) -> str:
    """
    Convert an expression string into a LaTeX string.

    Returns the original expression if it cannot be parsed.
    """
    if not expr.strip():
        return "1"
    try:
        normalized = _normalize_expr(expr)
        return _strip_float_zeros(latex(sympify(normalized)))
    except Exception:
        return expr

def _clean_factors(factor_list: list[str]) -> list[str]:
    """
    Normalize factor strings by stripping neutral factors and formatting signs.
    """
    cleaned = []
    for f in factor_list:
        # remove leading "1*" and extra parentheses
        f = re.sub(r'\b1\*', '', f)

        # remove outer parentheses if it's just 1*(...) → (...)
        f = re.sub(r'^1\*\((.*)\)$', r'(\1)', f)

        # remove .0 from integers
        f = _strip_float_zeros(f)

        # if not already wrapped in parentheses and contains '+' or '-', add ()
        if re.search(r'[+-]', f) and not f.startswith('('):
            f = f'({f})'

        cleaned.append(f)
    return cleaned


def _normalize_expr(expr: str) -> str:
    """
    Normalize a polynomial expression by inserting implicit multiplications
    and converting '^' to '**'.
    """
    # insert multiplication sign between parentheses
    expr = re.sub(r'\)\(', ')*(', expr)

    # number or variable followed by "(" -> insert *
    expr = re.sub(r'(\w)\(', r'\1*(', expr)

    # ")" followed by number or variable -> insert *
    expr = re.sub(r'\)(\w)', r')*\1', expr)

    # convert power operator
    expr = re.sub(r'\^', '**', expr)

    # insert * between a number and a variable
    expr = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr)

    return expr


def _strip_float_zeros(text: str) -> str:
    """
    Strip trailing '.0' from integer-like numbers inside a string.
    """
    return re.sub(r'(?<!\d)(-?\d+)\.0(?!\d)', r'\1', text)


def array2latex(array: list[float | int]) -> str:
    """
    Convert a coefficient array into a LaTeX polynomial string.

    Example:
        [1, 0, -3]  ->  "s^{2} - 3"

    The first element corresponds to the highest power.
    """

    if not array:
        return "1"

    degree = len(array) - 1
    terms: list[tuple[str, str]] = []

    for index, coeff in enumerate(array):
        power = degree - index

        # Skip zero coefficients
        if coeff == 0:
            continue

        # Convert float like 2.0 -> 2
        if isinstance(coeff, float) and coeff.is_integer():
            coeff = int(coeff)

        # Determine sign and absolute value
        sign = "-" if coeff < 0 else "+"
        abs_coeff = abs(coeff)

        # Build term depending on power
        if power == 0:
            term = f"{abs_coeff}"
        elif power == 1:
            if abs_coeff == 1:
                term = "s"
            else:
                term = f"{abs_coeff}s"
        else:
            if abs_coeff == 1:
                term = f"s^{{{power}}}"
            else:
                term = f"{abs_coeff}s^{{{power}}}"

        terms.append((sign, term))

    if not terms:
        return "0"

    # First term keeps its sign only if negative
    first_sign, first_term = terms[0]
    result = f"-{first_term}" if first_sign == "-" else first_term

    # Remaining terms
    for sign, term in terms[1:]:
        result += f" {sign} {term}"

    return result
