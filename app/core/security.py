from pwdlib import PasswordHash


# 建立 PasswordHash instance
# recommended() 會使用推薦的安全設定
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """將明文密碼轉成安全的 password hash。"""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """驗證明文密碼是否符合資料庫中的 hash。"""
    return password_hash.verify(password, hashed_password)
