import random, string

_ALPH = string.ascii_lowercase + string.digits

def short_slug(n: int = 6) -> str:
    # avoid confusing chars
    safe = _ALPH.replace('l','').replace('1','').replace('0','').replace('o','')
    return "".join(random.choice(safe) for _ in range(n))
