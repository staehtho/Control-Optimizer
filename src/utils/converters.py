import re
from sympy import expand, Poly, symbols, factor, simplify


def str2array(text: str) -> list[float]:

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
    s = symbols('s')

    # insert multiplication sign between parentheses
    expr = re.sub(r'\)\(', ')*(', expr)

    # number followed by "(" -> insert *
    expr = re.sub(r'(\w)\(', r'\1*(', expr)

    # ")" followed by number or variable -> insert *
    expr = re.sub(r'\)(\w)', r')*\1', expr)

    # convert power operator
    expr = re.sub(r'\^', '**', expr)

    # insert * between a number and a variable
    expr = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr)

    expanded = expand(expr)
    coefficients = Poly(expanded, s).all_coeffs()
    return [float(c) for c in coefficients]


def array2binominal(coefficients: list[float]) -> str:
    s = symbols('s')

    # convert all floats to float
    coefficients = [float(c) for c in coefficients]

    # create polynomial
    poly = Poly(coefficients, s).as_expr()

    # factor polynomial
    factored = factor(poly)

    # get factors as a list
    factors = factored.as_ordered_factors()

    normalized_factors = []
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
            f_str = str(normalized)

            # remove 1* in front of s
            f_str = re.sub(r'\b1\*', '', f_str)

            # remove trailing .0 for integers
            f_str = re.sub(r'(\d+)\.0', r'\1', f_str)

            normalized_factors.append(f_str)

            # multiply the lc into the final gain
            final_gain *= lc

    normalized_factors = _clean_factors(normalized_factors)
    # format final gain
    if float(final_gain) == 1.0:
        gain_str = ''
    elif float(final_gain).is_integer():
        gain_str = str(int(final_gain)) + '*'
    else:
        gain_str = str(final_gain) + '*'

    # join factors
    result = ''.join(normalized_factors)
    result = f"{gain_str}{result}"
    # remove (*)
    return re.sub(r'^\((.*)\)$', r'\1', result)

def _clean_factors(factor_list: list[str]) -> list[str]:
    cleaned = []
    for f in factor_list:
        # remove leading "1*" and extra parentheses
        f = re.sub(r'\b1\*', '', f)

        # remove outer parentheses if it's just 1*(...) → (...)
        f = re.sub(r'^1\*\((.*)\)$', r'(\1)', f)

        # remove .0 from integers
        f = re.sub(r'(\d+)\.0', r'\1', f)

        # if not already wrapped in parentheses and contains '+' or '-', add ()
        if re.search(r'[+-]', f) and not f.startswith('('):
            f = f'({f})'

        cleaned.append(f)
    return cleaned