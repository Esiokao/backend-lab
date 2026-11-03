#!/bin/sh
set -eu

# --proxy-headers：信任反向代理的 X-Forwarded-*，讓 request.client.host
# 是真實使用者 IP（rate limit 的 per-IP 桶才不會全站共用一個）。
# 信任模型：nginx 端用 $remote_addr「覆寫」X-Forwarded-For（見 nginx/*.conf），
# client 塞的假 XFF 到不了 api，所以 FORWARDED_ALLOW_IPS 預設放寬為 *；
# 未來若出現多層代理（XFF 會累加鏈），把這個 env 設成代理層的網段即可。
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}"
