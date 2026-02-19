from models import PlantModel

import pytest

@pytest.mark.parametrize(
    "num, expected",
    [
        ([1, 2, 3, 4], True),
        ([], False),
    ]
)
def test_num(num, expected):
    model = PlantModel()

    model.num = num
    assert model.is_valid == expected