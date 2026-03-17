from sympy import symbols, Poly, factor, simplify, expand
import re


def poly_to_normalized_binoms(coeffs):
    s = symbols('s')

    # convert all floats to float
    coeffs = [float(c) for c in coeffs]

    # create polynomial
    poly = Poly(coeffs, s).as_expr()

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

    normalized_factors = clean_factors(normalized_factors)
    # format final gain
    if float(final_gain) == 1.0:
        gain_str = ''
    elif float(final_gain).is_integer():
        gain_str = str(int(final_gain)) + '*'
    else:
        gain_str = str(final_gain) + '*'

    # join factors
    result = ''.join(normalized_factors)
    return f"{gain_str}{result}"


def clean_factors(factor_list):
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


# ----------------------------
if __name__ == '__main__':
    s = symbols('s')

    expr = "s(5s+1 )(s+5)(s-1)(s+1)^3"
    print(expr)

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
    coeffs = Poly(expanded, s).all_coeffs()
    coeffs = [float(c) for c in coeffs]

    print(poly_to_normalized_binoms(coeffs))
