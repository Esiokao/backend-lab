import pytest
from pydantic import ValidationError

from app.schemas.User import AdminUserPatch, UserCreate, UserPatch, UserUpdate


def _create_data(name: str) -> dict:
    return {"name": name, "email": "a@example.com", "password": "sup3rsecret"}


def test_name_is_trimmed():
    # 前後空白應被修剪，與前端 zod .trim() 同標準。
    assert UserCreate(**_create_data("  Pi Tester  ")).name == "Pi Tester"
    assert UserUpdate(name="\t王小明\n", email="a@example.com").name == "王小明"


def test_name_whitespace_only_rejected():
    # 純空白繞過 min_length 的洞：長度 > 0 但沒有內容，必須 422。
    with pytest.raises(ValidationError):
        UserCreate(**_create_data("   "))

    with pytest.raises(ValidationError):
        UserUpdate(name="   ", email="a@example.com")


def test_name_empty_rejected():
    with pytest.raises(ValidationError):
        UserCreate(**_create_data(""))


def test_name_max_length_still_enforced():
    with pytest.raises(ValidationError):
        UserCreate(**_create_data("a" * 101))


def test_name_internal_spaces_kept():
    # 名字內部的正常空格（英文全名）必須保留。
    assert UserCreate(**_create_data("Pi Tester")).name == "Pi Tester"


def test_optional_name_none_passes():
    # PATCH 的 name 是 optional：沒給就是 None，不該被 validator 波及。
    assert AdminUserPatch().name is None
    assert UserPatch().name is None
    assert AdminUserPatch(name="  X  ").name == "X"
