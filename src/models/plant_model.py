from dataclasses import dataclass, field


@dataclass
class PlantModel:
    num: list[float] = field(default_factory=list)
    den: list[float] = field(default_factory=list)
    tf: str = r"\frac{b_q s^q + b_{q-1}s^{q-1} + \ldots + b_1 s + b_0}{a_n s^n + a_{n-1}s^{n-1} + \ldots + a_1 s + a_0}"

    @property
    def is_valid(self) -> bool:
        if len(self.num) == 0 or len(self.den) == 0:
            return False
        if self.num[0] == 0 or self.den[0] == 0:
            return False
        if len(self.den) < len(self.num):
            return False
        return True
