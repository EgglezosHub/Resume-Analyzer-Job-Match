# app/utils/slug.py
import random, string
_ALPH = (string.ascii_lowercase + string.digits).replace('l','').replace('1','').replace('0','').replace('o','')

def short_slug(n: int = 10) -> str:
    return "".join(random.choice(_ALPH) for _ in range(n))

