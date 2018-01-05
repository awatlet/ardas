import numpy as np


def polynomial(freq, coefs):
    """Compute polynomial using Horner method"""

    result = coefs[-1]
    for i in range(-2, -len(coefs) - 1, -1):
        result = result * freq + coefs[i]
    assert isinstance(result, float)
    return result


def running_average(n):
    l = []
    average = None
    while True:
        new_elt = yield average
        if len(l) == n:
            del l[0]
        l.append(new_elt)
        if len(l) > 0:
            average = sum(l) / len(l)
        else:
            average = np.nan

if __name__ == '__main__':
    t = polynomial(25000, [-16.9224032438, 0.0041525221, -1.31475837290789e-07, 2.39122208189129e-12,
                           -1.72530800355418e-17])
    print(t)
