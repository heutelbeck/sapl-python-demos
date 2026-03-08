"""MCP server for internal data analytics platform.

Exposes tools, resources, and prompts for three departments:
marketing (campaign analytics), engineering (ML pipelines),
and compliance (audit, GDPR).

Authorization is handled by the SAPL middleware which intercepts all
MCP operations globally. No per-component auth= is needed.
"""

import logging
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import Field
from sapl_base import PdpClient, PdpConfig
from sapl_base.constraint_engine import ConstraintEnforcementService

from handlers import AccessLoggingProvider, FilterByClassificationProvider, LimitResultsProvider
from sapl_fastmcp.context import SubscriptionContext
from sapl_fastmcp.decorators import post_enforce, pre_enforce
from sapl_fastmcp.middleware import SAPLMiddleware

logging.basicConfig(level=logging.INFO)
logging.getLogger("sapl.mcp.middleware").setLevel(logging.DEBUG)
logger = logging.getLogger("sapl.mcp.analytics")

pdp = PdpClient(PdpConfig(
    base_url="http://localhost:8443",
    allow_insecure_connections=True,
))

constraint_service = ConstraintEnforcementService()
constraint_service.register_runnable(AccessLoggingProvider())
constraint_service.register_method_invocation(LimitResultsProvider())
constraint_service.register_filter_predicate(FilterByClassificationProvider())

auth = JWTVerifier(
    jwks_uri="http://localhost:8080/realms/mcp/protocol/openid-connect/certs",
    issuer="http://localhost:8080/realms/mcp",
)

mcp = FastMCP(
    name="analytics",
    auth=auth,
    instructions=(
        "Internal data analytics platform. Provides access to public metrics, "
        "customer data, ML model management, and compliance operations. "
        "Use tools to query data and perform actions, resources to browse "
        "available datasets and metadata, and prompts to generate analyses."
    ),
    middleware=[SAPLMiddleware(pdp, constraint_service)],
)


async def _purge_finalize(decision, ctx: SubscriptionContext) -> None:
    """Demo finalize callback for purge operations.

    In production this would commit or rollback a database transaction.
    """
    logger.info(
        "purge_finalize: decision=%s, dataset=%s",
        decision.decision.value,
        ctx.arguments.get("dataset_id"),
    )


# ---------------------------------------------------------------------------
# Tools -- data querying, export, ML, and compliance operations
# ---------------------------------------------------------------------------


@mcp.tool(
    title="Query Public Data",
    description=(
        "Query anonymized, aggregate datasets such as website traffic, "
        "product usage metrics, and conversion funnels. Results contain "
        "no personally identifiable information. Specify a dataset name "
        "and optional date range."
    ),
    tags={"public"},
)
@pre_enforce()
def query_public_data(
    dataset: Annotated[str, Field(description="Name of the dataset to query, e.g. 'web_traffic' or 'product_metrics'")],
    date_range: Annotated[str, Field(description="Time range for the query, e.g. 'last_30d', 'last_7d', or '2025-01-01:2025-01-31'")] = "last_30d",
) -> dict:
    """Query anonymized public datasets."""
    return {
        "dataset": dataset,
        "date_range": date_range,
        "rows": 14823,
        "columns": ["date", "page_views", "unique_visitors", "bounce_rate"],
        "sample": [
            {"date": "2025-01-15", "page_views": 12450, "unique_visitors": 8721, "bounce_rate": 0.34},
            {"date": "2025-01-16", "page_views": 13102, "unique_visitors": 9044, "bounce_rate": 0.31},
            {"date": "2025-01-17", "page_views": 11987, "unique_visitors": 8390, "bounce_rate": 0.36},
        ],
    }


@mcp.tool(
    title="Query Customer Data",
    description=(
        "Query customer records including names, emails, purchase history, "
        "and segmentation data. Results contain PII and are subject to "
        "GDPR and internal data handling policies. Specify a segment or "
        "filter criteria."
    ),
    tags={"pii"},
)
@pre_enforce(resource=lambda ctx: {"name": ctx.component.name, "tags": list(ctx.component.tags), "segment": ctx.arguments.get("segment")}, stealth=True)
def query_customer_data(
    segment: Annotated[str, Field(description="Customer segment to query, e.g. 'high_value', 'at_risk', 'new_customers', or 'enterprise'")],
    limit: Annotated[int, Field(description="Maximum number of customer records to return")] = 10,
) -> dict:
    """Query customer records containing PII."""
    return {
        "segment": segment,
        "total_matches": 2847,
        "limit": limit,
        "records": [
            {
                "customer_id": "C-10042",
                "name": "Alice Johnson",
                "email": "alice.johnson@example.com",
                "segment": segment,
                "lifetime_value": 1250.00,
                "last_purchase": "2025-01-10",
            },
            {
                "customer_id": "C-10078",
                "name": "Bob Martinez",
                "email": "bob.martinez@example.com",
                "segment": segment,
                "lifetime_value": 890.50,
                "last_purchase": "2025-01-12",
            },
            {
                "customer_id": "C-10135",
                "name": "Carol Chen",
                "email": "carol.chen@example.com",
                "segment": segment,
                "lifetime_value": 2100.75,
                "last_purchase": "2025-01-14",
            },
        ],
    }


@mcp.tool(
    title="Export CSV",
    description=(
        "Export query results as a CSV file. The exported data leaves the "
        "system boundary and may contain PII depending on the source query. "
        "Specify the query reference and desired columns."
    ),
    tags={"pii", "export"},
)
@pre_enforce(action="export_data", stealth=True)
def export_csv(
    query_ref: Annotated[str, Field(description="Reference ID of a previous query whose results should be exported")],
    columns: Annotated[str, Field(description="Comma-separated list of columns to include, or 'all' for every column")] = "all",
) -> dict:
    """Export query results as CSV. Data leaves the system boundary."""
    return {
        "query_ref": query_ref,
        "columns": columns,
        "format": "csv",
        "rows_exported": 2847,
        "file_size_bytes": 184320,
        "download_url": "/exports/export-20250115-001.csv",
        "expires_at": "2025-01-16T00:00:00Z",
    }


@mcp.tool(
    title="Run ML Model",
    description=(
        "Execute a trained ML model against a specified dataset. Returns "
        "predictions, confidence scores, and model performance metrics. "
        "Specify the model identifier and target dataset."
    ),
    tags={"engineering"},
)
@post_enforce(resource=lambda ctx: {"name": ctx.component.name, "tags": list(ctx.component.tags), "model": ctx.arguments.get("model_id"), "result_summary": ctx.return_value})
def run_model(
    model_id: Annotated[str, Field(description="Identifier of the ML model to execute, e.g. 'churn-predictor-v3'")],
    dataset: Annotated[str, Field(description="Name of the dataset to run the model against")],
) -> dict:
    """Execute an ML model against a dataset."""
    return {
        "model_id": model_id,
        "dataset": dataset,
        "status": "completed",
        "predictions_count": 5000,
        "metrics": {
            "accuracy": 0.924,
            "precision": 0.891,
            "recall": 0.937,
            "f1_score": 0.914,
        },
        "output_location": f"/models/{model_id}/predictions/run-20250115",
    }


@mcp.tool(
    title="Manage Pipelines",
    description=(
        "Create, read, update, or delete ETL data pipelines. Pipelines "
        "define scheduled data transformations from source to destination. "
        "Specify the operation (list, get, create, update, delete) and "
        "pipeline identifier."
    ),
    tags={"engineering"},
)
@pre_enforce()
def manage_pipelines(
    operation: Annotated[str, Field(description="CRUD operation to perform: 'list', 'get', 'create', 'update', or 'delete'")],
    pipeline_id: Annotated[str, Field(description="Identifier of the pipeline to operate on, e.g. 'etl-web-traffic'. Required for get/update/delete")] = "",
) -> dict:
    """CRUD operations on ETL data pipelines."""
    if operation == "list":
        return {
            "operation": "list",
            "pipelines": [
                {
                    "pipeline_id": "etl-web-traffic",
                    "name": "Web Traffic Aggregation",
                    "schedule": "0 2 * * *",
                    "status": "active",
                    "last_run": "2025-01-15T02:00:00Z",
                },
                {
                    "pipeline_id": "etl-customer-segments",
                    "name": "Customer Segmentation Refresh",
                    "schedule": "0 4 * * 0",
                    "status": "active",
                    "last_run": "2025-01-12T04:00:00Z",
                },
                {
                    "pipeline_id": "etl-model-features",
                    "name": "ML Feature Engineering",
                    "schedule": "0 3 * * *",
                    "status": "paused",
                    "last_run": "2025-01-10T03:00:00Z",
                },
            ],
        }
    return {
        "operation": operation,
        "pipeline_id": pipeline_id or "etl-web-traffic",
        "status": "success",
        "message": f"Pipeline {pipeline_id or 'etl-web-traffic'} {operation} completed.",
    }


@mcp.tool(
    title="Purge Dataset",
    description=(
        "Permanently delete a dataset and all associated records. This is "
        "an irreversible, destructive operation used primarily for GDPR "
        "right-to-erasure compliance. Requires the dataset identifier and "
        "a reason for the deletion."
    ),
    tags={"destructive", "compliance"},
)
@pre_enforce(finalize=_purge_finalize, stealth=True)
def purge_dataset(
    dataset_id: Annotated[str, Field(description="Identifier of the dataset to permanently delete")],
    reason: Annotated[str, Field(description="Justification for the deletion, e.g. 'GDPR right-to-erasure request #12345'")],
) -> dict:
    """Permanently delete a dataset. Irreversible."""
    return {
        "dataset_id": dataset_id,
        "reason": reason,
        "status": "purged",
        "records_deleted": 15234,
        "audit_reference": "AUDIT-2025-0115-0042",
        "timestamp": "2025-01-15T14:30:00Z",
    }


@mcp.tool(
    title="List Data Exports",
    description=(
        "List recent data exports with classification levels. Returns export "
        "records that may be filtered by policy obligations based on the "
        "caller's clearance level."
    ),
    tags={"export"},
)
@pre_enforce()
def list_data_exports(
    department: Annotated[str, Field(description="Department to filter exports for, or 'all' for every department")] = "all",
) -> list[dict]:
    """List recent data exports with classification levels."""
    return [
        {
            "export_id": "EXP-001",
            "dataset": "web_traffic",
            "department": "marketing",
            "classification": "public",
            "rows": 14823,
            "exported_at": "2025-01-15T10:00:00Z",
        },
        {
            "export_id": "EXP-002",
            "dataset": "customer_segments",
            "department": "marketing",
            "classification": "confidential",
            "rows": 2847,
            "exported_at": "2025-01-15T11:30:00Z",
        },
        {
            "export_id": "EXP-003",
            "dataset": "campaign_metrics",
            "department": "marketing",
            "classification": "internal",
            "rows": 5200,
            "exported_at": "2025-01-15T12:15:00Z",
        },
    ]


# ---------------------------------------------------------------------------
# Resources -- browsable metadata and catalogs
# ---------------------------------------------------------------------------


@mcp.resource(
    "data://public/summary",
    title="Public Datasets Summary",
    description=(
        "Lists all available anonymized, public datasets with their schemas, "
        "row counts, and last-updated timestamps. Use this to discover what "
        "data is available before running queries."
    ),
    tags={"public"},
    mime_type="text/plain",
)
@pre_enforce()
def public_summary() -> str:
    """Available public datasets with schemas."""
    return (
        "| Dataset              | Rows    | Updated    | Columns                                      |\n"
        "|----------------------|---------|------------|----------------------------------------------|\n"
        "| web_traffic          | 1.2M    | 2025-01-15 | date, page_views, unique_visitors, bounce_rate |\n"
        "| product_metrics      | 340K    | 2025-01-14 | date, product_id, views, add_to_cart, purchases |\n"
        "| conversion_funnels   | 89K     | 2025-01-15 | date, funnel_step, users_entered, users_completed |\n"
        "| campaign_performance | 156K    | 2025-01-13 | date, campaign_id, impressions, clicks, spend   |\n"
    )


@mcp.resource(
    "data://customers/segments",
    title="Customer Segments",
    description=(
        "Customer segmentation definitions including segment names, criteria, "
        "and population sizes. Contains PII-adjacent information (segment "
        "membership counts and behavioral criteria)."
    ),
    tags={"pii"},
    mime_type="text/plain",
)
@pre_enforce(stealth=True)
def customer_segments() -> str:
    """Customer segmentation definitions."""
    return (
        "| Segment           | Criteria                                  | Size  | Avg LTV  |\n"
        "|-------------------|-------------------------------------------|-------|----------|\n"
        "| high_value        | lifetime_value > 1000, purchases >= 5     | 2,847 | $1,450   |\n"
        "| at_risk           | no_purchase_days > 90, prev_active = true | 1,203 | $620     |\n"
        "| new_customers     | account_age_days < 30                     | 4,521 | $85      |\n"
        "| enterprise        | company_size > 500, plan = enterprise     | 312   | $12,300  |\n"
    )


@mcp.resource(
    "data://models/catalog",
    title="ML Model Catalog",
    description=(
        "Registry of available ML models with descriptions, training dates, "
        "and performance metrics. Use this to find model identifiers before "
        "running models."
    ),
    tags={"engineering"},
    mime_type="text/plain",
)
@pre_enforce()
def model_catalog() -> str:
    """ML models with descriptions and metrics."""
    return (
        "| Model ID               | Description                        | Trained    | Accuracy | F1    |\n"
        "|------------------------|------------------------------------|------------|----------|-------|\n"
        "| churn-predictor-v3     | Customer churn risk scoring        | 2025-01-10 | 0.924    | 0.914 |\n"
        "| ltv-estimator-v2       | Customer lifetime value prediction | 2025-01-08 | 0.887    | 0.862 |\n"
        "| segment-classifier-v1  | Auto-segmentation classifier       | 2024-12-20 | 0.951    | 0.943 |\n"
        "| anomaly-detector-v4    | Data pipeline anomaly detection    | 2025-01-12 | 0.978    | 0.965 |\n"
    )


@mcp.resource(
    "data://audit/log",
    title="Audit Log",
    description=(
        "Recent data access and authorization log entries. Shows who accessed "
        "what data, when, and whether the access was authorized. Used for "
        "compliance monitoring and incident investigation."
    ),
    tags={"compliance"},
    mime_type="text/plain",
)
@pre_enforce(stealth=True)
def audit_log() -> str:
    """Recent data access and authorization log."""
    return (
        "| Timestamp           | User            | Action              | Resource                  | Result     |\n"
        "|---------------------|-----------------|---------------------|---------------------------|------------|\n"
        "| 2025-01-15 14:22:01 | analyst@corp    | query_customer_data | customers/high_value      | authorized |\n"
        "| 2025-01-15 14:18:45 | engineer@corp   | run_model           | churn-predictor-v3        | authorized |\n"
        "| 2025-01-15 14:15:30 | intern@corp     | export_csv          | customers/segments        | denied     |\n"
        "| 2025-01-15 14:10:12 | compliance@corp | purge_dataset       | dataset-legacy-2023       | authorized |\n"
        "| 2025-01-15 14:05:00 | analyst@corp    | query_public_data   | web_traffic               | authorized |\n"
    )


# ---------------------------------------------------------------------------
# Resource templates -- parameterized resource access
# ---------------------------------------------------------------------------


@mcp.resource(
    "data://models/{model_id}",
    title="ML Model Details",
    description=(
        "Detailed information for a specific ML model including architecture, "
        "training configuration, feature list, and performance history. "
        "Specify the model_id from the model catalog."
    ),
    tags={"engineering"},
    mime_type="text/plain",
)
@pre_enforce()
def model_details(
    model_id: Annotated[str, Field(description="Identifier of the model from the catalog, e.g. 'churn-predictor-v3' or 'ltv-estimator-v2'")],
) -> str:
    """Details for a specific ML model."""
    models = {
        "churn-predictor-v3": (
            "Model: churn-predictor-v3\n"
            "Type: Gradient Boosted Trees (XGBoost)\n"
            "Features: 42 (purchase_frequency, days_since_last, support_tickets, ...)\n"
            "Training set: 120K customers, 2024-06 to 2024-12\n"
            "Accuracy: 0.924 | Precision: 0.891 | Recall: 0.937 | F1: 0.914\n"
            "Deployed: 2025-01-10 | Retrain schedule: monthly"
        ),
        "ltv-estimator-v2": (
            "Model: ltv-estimator-v2\n"
            "Type: Linear Regression with regularization\n"
            "Features: 28 (order_count, avg_order_value, tenure_months, ...)\n"
            "Training set: 95K customers, 2024-01 to 2024-12\n"
            "Accuracy: 0.887 | MAE: $142.30 | R2: 0.862\n"
            "Deployed: 2025-01-08 | Retrain schedule: quarterly"
        ),
    }
    return models.get(model_id, f"Model '{model_id}' not found in catalog.")


@mcp.resource(
    "data://customers/{segment}/{field}",
    title="Customer Segment Field",
    description=(
        "Access a specific data field for a customer segment. Fields include "
        "names, emails, purchase_history, and demographics. Contains PII -- "
        "access may be restricted based on the field requested and the "
        "caller's GDPR training status."
    ),
    tags={"pii"},
    mime_type="text/plain",
)
@pre_enforce(stealth=True)
def customer_segment_field(
    segment: Annotated[str, Field(description="Customer segment name, e.g. 'high_value', 'at_risk', 'new_customers', or 'enterprise'")],
    field: Annotated[str, Field(description="Data field to retrieve: 'names', 'emails', 'purchase_history', or 'demographics'")],
) -> str:
    """Access a specific field of a customer segment. Contains PII."""
    data = {
        ("high_value", "names"): (
            "Alice Johnson\nBob Martinez\nCarol Chen\nDavid Kim\nEva Mueller"
        ),
        ("high_value", "emails"): (
            "alice.johnson@example.com\nbob.martinez@example.com\n"
            "carol.chen@example.com\ndavid.kim@example.com\neva.mueller@example.com"
        ),
        ("high_value", "purchase_history"): (
            "| Customer     | Orders | Total     | Last Purchase |\n"
            "|--------------|--------|-----------|---------------|\n"
            "| Alice Johnson | 12     | $1,250.00 | 2025-01-10    |\n"
            "| Bob Martinez  | 8      | $890.50   | 2025-01-12    |\n"
            "| Carol Chen    | 15     | $2,100.75 | 2025-01-14    |"
        ),
        ("high_value", "demographics"): (
            "| Metric        | Value       |\n"
            "|---------------|-------------|\n"
            "| Avg age       | 34          |\n"
            "| Top regions   | US-CA, DE, UK |\n"
            "| Segment size  | 2,847       |"
        ),
    }
    key = (segment, field)
    if key in data:
        return data[key]
    return f"No data for segment='{segment}', field='{field}'."


# ---------------------------------------------------------------------------
# Prompts -- reusable analysis templates
# ---------------------------------------------------------------------------


@mcp.prompt(
    title="Analyze Trends",
    description=(
        "Analyze trends in a specified dataset over a given time period. "
        "Produces a structured analysis including key metrics, trends, "
        "and actionable insights. Works with public, anonymized data."
    ),
    tags={"public"},
)
@pre_enforce()
def analyze_trends(
    dataset: Annotated[str, Field(description="Name of the dataset to analyze trends for")],
    time_period: Annotated[str, Field(description="Time period for trend analysis, e.g. 'last_30d' or 'last_7d'")] = "last_30d",
) -> str:
    """Analyze trends in a dataset."""
    return (
        f"Analyze the following trends in the '{dataset}' dataset "
        f"for the period '{time_period}':\n\n"
        "1. Identify the top 3 metrics with the most significant changes.\n"
        "2. Calculate week-over-week and month-over-month growth rates.\n"
        "3. Highlight any anomalies or outliers in the data.\n"
        "4. Provide actionable recommendations based on the trends.\n\n"
        f"Use the query_public_data tool with dataset='{dataset}' "
        f"and date_range='{time_period}' to retrieve the data first."
    )


@mcp.prompt(
    title="Generate Report",
    description=(
        "Generate a formatted report for stakeholders from query results. "
        "The report may include customer data and PII depending on the "
        "source data. Specify the report type and target audience."
    ),
    tags={"pii"},
)
@pre_enforce()
def generate_report(
    report_type: Annotated[str, Field(description="Type of report to generate, e.g. 'sales_summary', 'churn_analysis', or 'quarterly_review'")],
    audience: Annotated[str, Field(description="Target audience for the report: 'management', 'engineering', or 'board'")] = "management",
) -> str:
    """Generate a formatted stakeholder report."""
    return (
        f"Generate a '{report_type}' report for the '{audience}' audience.\n\n"
        "The report should include:\n"
        "1. Executive summary (2-3 sentences).\n"
        "2. Key metrics table with current values and period-over-period changes.\n"
        "3. Customer segment breakdown with population sizes and trends.\n"
        "4. Recommendations section with prioritized action items.\n\n"
        "Format the output as a professional document with headers, tables, "
        "and bullet points. Use query_customer_data and query_public_data tools "
        "to gather the necessary data."
    )


@mcp.prompt(
    title="Compliance Review",
    description=(
        "Review data handling practices for regulatory compliance. Checks "
        "recent data access patterns, export activity, and deletion requests "
        "against GDPR and internal policies."
    ),
    tags={"compliance"},
)
@pre_enforce()
def compliance_review(
    regulation: Annotated[str, Field(description="Regulation to review against, e.g. 'GDPR', 'CCPA', or 'HIPAA'")] = "GDPR",
    review_period: Annotated[str, Field(description="Time period to review, e.g. 'last_7d' or 'last_30d'")] = "last_7d",
) -> str:
    """Review data handling for regulation compliance."""
    return (
        f"Conduct a compliance review against '{regulation}' requirements "
        f"for the period '{review_period}'.\n\n"
        "Review the following areas:\n"
        "1. Data access patterns -- who accessed PII and was it authorized?\n"
        "2. Data exports -- were any exports made without proper authorization?\n"
        "3. Deletion requests -- are all right-to-erasure requests processed timely?\n"
        "4. Retention policies -- is any data held beyond its retention period?\n\n"
        "Use the data://audit/log resource to review recent access events, "
        "and the data://customers/segments resource to verify data handling."
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
