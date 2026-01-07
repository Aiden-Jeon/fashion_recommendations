from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from databricks.sdk import WorkspaceClient
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db import query_sql, close_all_connections
from db import set_current_user_token  # OBO: set token per request
from settings import get_settings

app = FastAPI(title="Fashion Recommendations Dashboard")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

workspace = WorkspaceClient()
logger = logging.getLogger("fashion_app")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

settings = get_settings()


# OBO middleware: capture forwarded user token
@app.middleware("http")
async def inject_user_token(request: Request, call_next):
    token = request.headers.get("X-Forwarded-Access-Token")
    set_current_user_token(token)
    # Optional: enforce token for pages that require SQL
    # if not token and request.url.path not in ("/metrics", "/api/image"):
    #     return Response(status_code=401, content="Missing user token")
    response = await call_next(request)
    return response


@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources on app shutdown."""
    logger.info("Shutting down application...")
    close_all_connections()


def build_main_nav(active_slug: str) -> List[Dict[str, object]]:
    """Build main navigation menu."""
    nav_items = [
        {"slug": "bestsellers", "label": "베스트셀러 분석", "url": "/"},
        {"slug": "demographics", "label": "고객 인구통계", "url": "/demographics"},
        {"slug": "timeseries", "label": "시계열 분석", "url": "/timeseries"},
        {"slug": "explorer", "label": "상품 탐색기", "url": "/explorer"},
    ]
    for item in nav_items:
        item["active"] = item["slug"] == active_slug
    return nav_items


def get_image_path(article_id: int) -> str:
    """Get image path for article_id."""
    article_str = str(article_id).zfill(10)
    folder = article_str[:3]
    return f"{settings.volume_path}/images/{folder}/{article_str}.jpg"


def image_url(article_id: int) -> str:
    """Generate image URL for article."""
    return f"/api/image?article_id={article_id}"


@app.get("/", response_class=HTMLResponse)
def bestsellers(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    category: str = Query("ALL"),
    limit: int = Query(20, ge=1, le=100),
):
    """Bestseller products analysis page."""
    query = f"""
    SELECT 
      a.article_id,
      a.prod_name,
      a.product_type_name,
      a.product_group_name,
      a.colour_group_name,
      a.department_name,
      ps.num_transactions,
      ps.total_revenue,
      ps.unique_customers,
      ps.avg_price
    FROM {settings.full_table_name}.articles_synced a
    JOIN {settings.full_table_name}.product_sales_summary_synced ps
      ON a.article_id = ps.article_id
    WHERE 1=1
    """

    params = []
    if start_date:
        query += " AND ps.last_purchase_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND ps.last_purchase_date <= ?"
        params.append(end_date)
    if category != "ALL":
        query += " AND a.product_group_name = ?"
        params.append(category)

    query += f" ORDER BY ps.num_transactions DESC LIMIT {limit}"

    df = query_sql(query, params if params else None)

    # Available categories
    cat_query = f"""
    SELECT DISTINCT product_group_name 
    FROM {settings.full_table_name}.articles_synced 
    WHERE product_group_name IS NOT NULL
    ORDER BY product_group_name
    """
    categories_df = query_sql(cat_query)
    categories = ["ALL"] + categories_df["product_group_name"].tolist()

    # Prepare products data
    products = []
    for _, row in df.iterrows():
        products.append(
            {
                "article_id": int(row["article_id"]),
                "prod_name": row["prod_name"],
                "product_type_name": row["product_type_name"],
                "product_group_name": row["product_group_name"],
                "colour_group_name": row["colour_group_name"],
                "department_name": row["department_name"],
                "num_transactions": int(row["num_transactions"]),
                "total_revenue": float(row["total_revenue"]),
                "unique_customers": int(row["unique_customers"]),
                "avg_price": float(row["avg_price"]),
                "image_url": image_url(int(row["article_id"])),
            }
        )

    context = {
        "request": request,
        "main_nav": build_main_nav("bestsellers"),
        "products": products,
        "categories": categories,
        "filters": {
            "start_date": start_date or "",
            "end_date": end_date or "",
            "category": category,
            "limit": limit,
        },
    }

    return templates.TemplateResponse("bestsellers.html", context)


@app.get("/demographics", response_class=HTMLResponse)
def demographics(request: Request):
    """Customer demographics analysis page."""
    age_query = f"""
    SELECT 
      age_bin,
      COUNT(*) as count,
      AVG(total_spent) as avg_spent,
      AVG(num_purchases) as avg_purchases
    FROM {settings.full_table_name}.customer_demographics_synced
    WHERE age_bin IS NOT NULL
    GROUP BY age_bin
    ORDER BY age_bin
    """
    age_df = query_sql(age_query)

    club_query = f"""
    SELECT 
      club_member_status,
      COUNT(*) as count,
      AVG(total_spent) as avg_spent
    FROM {settings.full_table_name}.customer_demographics_synced
    WHERE club_member_status IS NOT NULL
    GROUP BY club_member_status
    """
    club_df = query_sql(club_query)

    news_query = f"""
    SELECT 
      fashion_news_frequency,
      COUNT(*) as count,
      AVG(total_spent) as avg_spent
    FROM {settings.full_table_name}.customer_demographics_synced
    WHERE fashion_news_frequency IS NOT NULL
    GROUP BY fashion_news_frequency
    """
    news_df = query_sql(news_query)

    # Charts
    age_chart = px.bar(
        age_df,
        x="age_bin",
        y="count",
        title="연령대별 고객 분포",
        labels={"age_bin": "연령대", "count": "고객 수"},
        color="count",
        color_continuous_scale="Blues",
    )
    age_chart.update_layout(template="plotly_white", showlegend=False, height=400)

    club_chart = px.pie(
        club_df,
        values="count",
        names="club_member_status",
        title="클럽 멤버 상태별 분포",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    club_chart.update_layout(height=400)

    news_chart = px.bar(
        news_df,
        x="fashion_news_frequency",
        y="count",
        title="패션 뉴스 구독 현황",
        labels={"fashion_news_frequency": "구독 빈도", "count": "고객 수"},
        color="avg_spent",
        color_continuous_scale="Viridis",
    )
    news_chart.update_layout(template="plotly_white", height=400)

    context = {
        "request": request,
        "main_nav": build_main_nav("demographics"),
        "age_chart": age_chart.to_html(include_plotlyjs=False, div_id="age-chart"),
        "club_chart": club_chart.to_html(include_plotlyjs=False, div_id="club-chart"),
        "news_chart": news_chart.to_html(include_plotlyjs=False, div_id="news-chart"),
        "age_stats": age_df.to_dict("records"),
        "club_stats": club_df.to_dict("records"),
        "news_stats": news_df.to_dict("records"),
    }

    return templates.TemplateResponse("demographics.html", context)


@app.get("/timeseries", response_class=HTMLResponse)
def timeseries(
    request: Request,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    granularity: str = Query("daily"),
):
    """Time series analysis page."""
    if granularity == "daily":
        group_by = "date"
        date_col = "date"
    elif granularity == "weekly":
        group_by = "year, week"
        date_col = "MIN(date)"
    else:  # monthly
        group_by = "year_month"
        date_col = "MIN(date)"

    query = f"""
    SELECT 
      {date_col} as date,
      SUM(num_transactions) as num_transactions,
      SUM(total_revenue) as total_revenue,
      SUM(unique_customers) as unique_customers,
      SUM(unique_products) as unique_products,
      AVG(avg_transaction_value) as avg_transaction_value
    FROM {settings.full_table_name}.time_series_sales_synced
    WHERE 1=1
    """

    params = []
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += f" GROUP BY {group_by} ORDER BY date"

    df = query_sql(query, params if params else None)

    revenue_chart = go.Figure()
    revenue_chart.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["total_revenue"],
            mode="lines+markers",
            name="총 매출",
            line=dict(color="#0062ff", width=3),
            marker=dict(size=6),
        )
    )
    revenue_chart.update_layout(
        title="매출 추이",
        xaxis_title="날짜",
        yaxis_title="매출액",
        template="plotly_white",
        height=400,
        hovermode="x unified",
    )

    transactions_chart = go.Figure()
    transactions_chart.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["num_transactions"],
            mode="lines+markers",
            name="거래 건수",
            line=dict(color="#00a159", width=3),
            marker=dict(size=6),
        )
    )
    transactions_chart.update_layout(
        title="거래 건수 추이",
        xaxis_title="날짜",
        yaxis_title="거래 건수",
        template="plotly_white",
        height=400,
        hovermode="x unified",
    )

    customers_chart = go.Figure()
    customers_chart.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["unique_customers"],
            mode="lines+markers",
            name="고객 수",
            line=dict(color="#ff6b6b", width=3),
            marker=dict(size=6),
        )
    )
    customers_chart.update_layout(
        title="고객 수 추이",
        xaxis_title="날짜",
        yaxis_title="고객 수",
        template="plotly_white",
        height=400,
        hovermode="x unified",
    )

    context = {
        "request": request,
        "main_nav": build_main_nav("timeseries"),
        "revenue_chart": revenue_chart.to_html(
            include_plotlyjs=False, div_id="revenue-chart"
        ),
        "transactions_chart": transactions_chart.to_html(
            include_plotlyjs=False, div_id="transactions-chart"
        ),
        "customers_chart": customers_chart.to_html(
            include_plotlyjs=False, div_id="customers-chart"
        ),
        "filters": {
            "start_date": start_date or "",
            "end_date": end_date or "",
            "granularity": granularity,
        },
        "granularities": ["daily", "weekly", "monthly"],
    }

    return templates.TemplateResponse("timeseries.html", context)


@app.get("/explorer", response_class=HTMLResponse)
def explorer(
    request: Request,
    search: str = Query(""),
    category: str = Query("ALL"),
    color: str = Query("ALL"),
    department: str = Query("ALL"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
):
    """Product explorer page."""
    query = f"""
    SELECT 
      a.article_id,
      a.prod_name,
      a.product_type_name,
      a.product_group_name,
      a.colour_group_name,
      a.department_name,
      a.detail_desc,
      COALESCE(ps.num_transactions, 0) as num_transactions,
      COALESCE(ps.total_revenue, 0) as total_revenue,
      COALESCE(ps.unique_customers, 0) as unique_customers
    FROM {settings.full_table_name}.articles_synced a
    LEFT JOIN {settings.full_table_name}.product_sales_summary_synced ps
      ON a.article_id = ps.article_id
    WHERE 1=1
    """

    params = []
    if search:
        query += " AND (a.prod_name LIKE ? OR a.detail_desc LIKE ?)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern])
    if category != "ALL":
        query += " AND a.product_group_name = ?"
        params.append(category)
    if color != "ALL":
        query += " AND a.colour_group_name = ?"
        params.append(color)
    if department != "ALL":
        query += " AND a.department_name = ?"
        params.append(department)

    # Total count
    count_query = f"SELECT COUNT(*) as total FROM ({query}) t"
    total_count = query_sql(count_query, params if params else None)["total"].iloc[0]

    # Pagination
    offset = (page - 1) * page_size
    query += f" ORDER BY COALESCE(ps.num_transactions, 0) DESC LIMIT {page_size} OFFSET {offset}"

    df = query_sql(query, params if params else None)

    # Filters
    cat_query = f"SELECT DISTINCT product_group_name FROM {settings.full_table_name}.articles_synced WHERE product_group_name IS NOT NULL ORDER BY product_group_name"
    categories = ["ALL"] + query_sql(cat_query)["product_group_name"].tolist()

    color_query = f"SELECT DISTINCT colour_group_name FROM {settings.full_table_name}.articles_synced WHERE colour_group_name IS NOT NULL ORDER BY colour_group_name"
    colors = ["ALL"] + query_sql(color_query)["colour_group_name"].tolist()

    dept_query = f"SELECT DISTINCT department_name FROM {settings.full_table_name}.articles_synced WHERE department_name IS NOT NULL ORDER BY department_name"
    departments = ["ALL"] + query_sql(dept_query)["department_name"].tolist()

    # Records
    products = []
    for _, row in df.iterrows():
        products.append(
            {
                "article_id": int(row["article_id"]),
                "prod_name": row["prod_name"],
                "product_type_name": row["product_type_name"],
                "product_group_name": row["product_group_name"],
                "colour_group_name": row["colour_group_name"],
                "department_name": row["department_name"],
                "detail_desc": row["detail_desc"] or "",
                "num_transactions": int(row["num_transactions"]),
                "total_revenue": float(row["total_revenue"]),
                "unique_customers": int(row["unique_customers"]),
                "image_url": image_url(int(row["article_id"])),
            }
        )

    total_pages = (total_count + page_size - 1) // page_size

    context = {
        "request": request,
        "main_nav": build_main_nav("explorer"),
        "products": products,
        "categories": categories,
        "colors": colors,
        "departments": departments,
        "filters": {
            "search": search,
            "category": category,
            "color": color,
            "department": department,
        },
        "pagination": {
            "current": page,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_prev": page > 1,
            "has_next": page < total_pages,
        },
    }

    return templates.TemplateResponse("explorer.html", context)


@app.get("/api/image")
def get_image(article_id: int = Query(...)):
    """Serve product image from volume."""
    try:
        image_path = get_image_path(article_id)
        response = workspace.files.download(image_path)
        data = response.contents.read()
        return Response(content=data, media_type="image/jpeg")
    except Exception as e:
        logger.warning(f"Image not found for article_id={article_id}: {e}")
        # 1x1 transparent PNG
        placeholder = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        return Response(content=placeholder, media_type="image/png")


@app.get("/metrics")
def metrics():
    """Metrics endpoint for monitoring and health checks."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "application": "Fashion Recommendations Dashboard",
        "version": "1.0.0",
    }
