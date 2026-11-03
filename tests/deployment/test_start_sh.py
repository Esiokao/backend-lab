# tests/deployment/unit/test_start_sh.py
#
# 防回歸 pin：uvicorn 必須開 --proxy-headers，否則 request.client.host
# 是 nginx 容器 IP——rate limit 的 per-IP 桶會全站共用一個，
# 而且這個錯誤是靜默的（功能看起來正常，只是擋錯對象）。
# 這個 flag 與 nginx conf 的 X-Forwarded-For $remote_addr（覆寫式）
# 是一對：見 nginx/nginx.prod.conf 的註解。

from pathlib import Path

START_SH = Path(__file__).resolve().parents[2] / "scripts" / "start.sh"


def test_start_sh_enables_proxy_headers():
    content = START_SH.read_text(encoding="utf-8")

    assert "--proxy-headers" in content
    assert "--forwarded-allow-ips" in content
