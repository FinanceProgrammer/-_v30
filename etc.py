def get_tick_unit(price):
    if price < 2000:
        return 1
    elif price < 5000:
        return 5
    elif price < 20000:
        return 10
    elif price < 50000:
        return 50
    elif price < 200000:
        return 100
    elif price < 500000:
        return 500
    else:
        return 1000

def get_hoga(price, n_ticks):
    """
    틱 단위 가격에서 시작해서, 매 틱마다 호가 단위를 재계산하며 ±n틱 이동한 가격 반환
    """
    if price % get_tick_unit(price) != 0:
        raise ValueError(f"{price}는 유효한 호가 가격이 아닙니다.")

    current_price = price
    direction = 1 if n_ticks > 0 else -1

    for _ in range(abs(n_ticks)):
        tick = get_tick_unit(current_price)
        current_price += direction * tick
    return current_price


