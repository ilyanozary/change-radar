from pricing import total_price as price


def checkout():
    return price(12, 3)


def invoice():
    return price(10, 2)


def stock_count():
    return 40
