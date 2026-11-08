"""SEO 基礎：robots.txt 與 sitemap.xml。

sitemap 由商品/分類表自動生成——新商品上架自動進清單，不用手維護。
absolute URL 從 request（含 X-Forwarded-* proxy headers）推導：
正式環境經 nginx + Cloudflare 代理，uvicorn --proxy-headers 已啟用，
scheme/host 會還原成訪客看到的 https://esiokao.shop。
"""

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select

from app.database import DbSession
from app.models import Category, Product

router = APIRouter()

SITE_ROUTES = ["/", "/about"]


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt(request: Request) -> PlainTextResponse:
    base = str(request.base_url).rstrip("/")
    lines = [
        "User-agent: *",
        # 會員/後台區域對搜尋引擎無意義（登入牆後），不開放爬。
        "Disallow: /admin/",
        "Disallow: /app/",
        f"Sitemap: {base}/sitemap.xml",
    ]
    return PlainTextResponse("\n".join(lines))


@router.get("/sitemap.xml")
def sitemap_xml(request: Request, db: DbSession) -> Response:
    base = str(request.base_url).rstrip("/")
    products = db.scalars(select(Product.id).where(Product.is_active.is_(True))).all()
    categories = db.scalars(select(Category.id)).all()

    urls = [f"{base}{route}" for route in SITE_ROUTES]
    urls += [f"{base}/product/{pid}" for pid in products]
    urls += [f"{base}/?cat={cid}" for cid in categories]

    body = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *[f"  <url><loc>{u}</loc></url>" for u in urls],
            "</urlset>",
        ]
    )
    return Response(
        content=body,
        media_type="application/xml",
        headers={"Cache-Control": "no-store"},
    )
