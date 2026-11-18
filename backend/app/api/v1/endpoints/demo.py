from typing import Any

from fastapi import APIRouter, HTTPException


router = APIRouter(prefix="/demo", tags=["Sample & Demo Datasets"])

SAMPLE_SINGLE_STOCK = {
    "is_sample": True,
    "sample_notice": "Sample demonstration data. Not live SEC data. Note: Figures are illustrative old figures (2023-24 era) and not current.",
    "ticker": "NVDA",
    "prompt": "Evaluate revenue trajectory, core operating drivers, cloud/AI positioning, and risk factors.",
    "report": (
        "## Executive Investment Summary: NVIDIA Corporation (NVDA) [Sample Data]\n\n"
        "### 1. Revenue Trajectory & Operating Momentum\n"
        "NVIDIA Corporation delivered record-breaking performance in Q4, reporting total quarterly revenue of "
        "**$22.10 billion**, representing a **265% year-over-year increase** compared to $6.05 billion in the prior-year period. "
        "Full-year revenue reached $60.9 billion, up 126%, fueled predominantly by enterprise-wide infrastructure transformations across accelerated computing and generative artificial intelligence.\n\n"
        "* **Data Center Dominance:** Data Center segment revenue expanded to **$18.4 billion**, skyrocketing **409% year-over-year** [1].\n"
        "* **Operating Leverage & Margins:** Gross margins expanded to **76.0%**, benefiting from high-margin software stack integration (CUDA, TensorRT) alongside massive hardware volume shipment efficiencies [2].\n\n"
        "### 2. Core Technological Drivers & AI Positioning\n"
        "The primary catalyst behind this operating expansion is the global transition from general-purpose CPU computing to accelerated parallel computing:\n\n"
        "* **Hopper Architecture:** Enterprise adoption of the H100 Tensor Core GPU remained robust with supply chains scaling rapidly [1].\n"
        "* **Software Ecosystem Moat:** The CUDA software layer constitutes a defensible competitive moat with millions of developers.\n\n"
        "### 3. Material Risk Factors & Disclosures\n"
        "* **Export Restrictions:** US export controls regarding advanced semiconductor exports to China represent an ongoing headwind [1].\n"
        "* **Foundry & CoWoS Supply Limits:** Advanced packaging constraints dictate unit throughput limits.\n\n"
        "*(Note: This report is illustrative sample demonstration data (old 2023-24 era figures, not current). Not from a real document. Not investment advice.)*"
    ),
    "sentiment": "Revenue growth +265% YoY, gross margin 76% (Sample)",
    "metrics": {
        "source": "Sample data",
        "source_label": "Illustrative sample, not from a document",
        "source_badge": "Illustrative sample, not from a document",
        "revenue": 22.1,
        "revenue_label": "$22.1B",
        "revenue_source": "Illustrative sample, not from a document",
        "revenue_period": "Illustrative sample, not from a document",
        "growth_yoy": 265.0,
        "growth_label": "+265%",
        "growth_source": "Illustrative sample, not from a document",
        "growth_period": "Illustrative sample, not from a document",
        "gross_margin": 76.0,
        "margin_label": "76.0%",
        "margin_source": "Illustrative sample, not from a document",
        "margin_period": "Illustrative sample, not from a document",
        "primary_driver": "H100 Hopper & Accelerated Computing (Old sample)",
        "driver_source": "Illustrative sample, not from a document",
        "driver_period": "Illustrative sample, not from a document",
        "cloud_ai_revenue": "$18.4B Data Center",
        "sentiment": "Revenue growth +265% YoY, gross margin 76% (Sample)",
        "reason": None,
    },
    "sources": [
        {
            "score": 0.942,
            "text": "[Sample 1] NVIDIA Corporation reported record Q4 revenue of $22.1 billion, up 265% YoY. Data Center revenue grew 409% to $18.4 billion. Key risks include export control restrictions and supply chain limits.",
            "metadata": {"ticker": "NVDA", "source": "sample_filing_nvda.txt"},
        },
        {
            "score": 0.887,
            "text": "[Sample 2] Gross margins expanded to 76.0% for the quarter. Demand for accelerated computing platforms across cloud and enterprise software drove operating leverage.",
            "metadata": {"ticker": "NVDA", "source": "sample_filing_nvda.txt"},
        },
    ],
}

SAMPLE_COMPARISON = {
    "is_sample": True,
    "sample_notice": "Sample demonstration data. Not live SEC data. Note: Figures are illustrative old figures (2023-24 era) and not current.",
    "stock_a": "NVDA",
    "stock_b": "GOOGL",
    "prompt": "Conduct a side-by-side comparative financial analysis between NVDA and GOOGL.",
    "report": (
        "## Dual-Issuer Comparative Dossier: NVIDIA ($NVDA) vs. Alphabet ($GOOGL) [Sample Data]\n\n"
        "### 1. Revenue Momentum & Growth Multiples\n"
        "* **NVIDIA ($NVDA):** Delivered **265% YoY revenue growth** to **$22.1B**, powered by accelerated hardware and infrastructure buildout across enterprise and hyperscale customers [1].\n"
        "* **Alphabet ($GOOGL):** Reported revenue of **$86.3B**, representing a solid **13% YoY growth rate**, underpinned by durable search advertising demand and Google Cloud momentum [2].\n"
        "* **Multiples Comparison:** While Alphabet exhibits larger absolute volume ($86.3B vs. $22.1B), NVIDIA commands exponential growth velocity (+265% vs. +13%).\n\n"
        "### 2. Cloud & Artificial Intelligence Infrastructure Moats\n"
        "* **NVIDIA Compute Silicon:** Near-monopoly on high-performance accelerators backed by the CUDA software ecosystem.\n"
        "* **Google Full-Stack Synergy:** Vertically integrated AI stack with custom TPUs, hyperscale GCP infrastructure, and Gemini foundation models.\n\n"
        "### 3. Primary Risk Factors\n"
        "* **NVIDIA:** Supply chain dependencies (TSMC CoWoS packaging) and geopolitical export restrictions.\n"
        "* **Alphabet:** Digital ad cyclicality and antitrust litigation regarding search distribution.\n\n"
        "*(Note: Sample illustrative benchmark data (old 2023-24 era figures, not current). Not from a real document. Not investment advice.)*"
    ),
    "comparison_metrics": [
        {
            "metric": "Revenue ($B)",
            "NVDA": 22.1,
            "GOOGL": 86.3,
            "source": "Illustrative sample, not from a document",
            "period": "Illustrative sample, not from a document",
        },
        {
            "metric": "YoY Growth (%)",
            "NVDA": 265.0,
            "GOOGL": 13.0,
            "source": "Illustrative sample, not from a document",
            "period": "Illustrative sample, not from a document",
        },
        {
            "metric": "Gross Margin (%)",
            "NVDA": 76.0,
            "GOOGL": 56.5,
            "source": "Illustrative sample, not from a document",
            "period": "Illustrative sample, not from a document",
        },
    ],
    "sources": [
        {
            "score": 0.923,
            "text": "[Sample 1] NVIDIA reported record Q4 revenue of $22.1 billion, up 265% YoY on enterprise H100 GPU demand.",
            "metadata": {"ticker": "NVDA", "source": "sample_nvda.txt"},
        },
        {
            "score": 0.915,
            "text": "[Sample 2] Alphabet reported Q4 revenue of $86.3 billion, up 13% YoY, propelled by Search and Google Cloud momentum.",
            "metadata": {"ticker": "GOOGL", "source": "sample_googl.txt"},
        },
    ],
}

SAMPLE_COVERAGE = {
    "is_sample": True,
    "sample_notice": "Sample demonstration data. Not live SEC data. Note: Figures are illustrative old figures (2023-24 era) and not current.",
    "companies": [
        {
            "ticker": "NVDA",
            "name": "NVIDIA Corporation",
            "sector": "AI Compute & Silicon",
            "revenue": "$22.10B",
            "growth": "+265% YoY",
            "margin": "76.0%",
            "trend": "up",
            "badge": "Sample Data (old 2023-24)",
            "source": "Illustrative sample, not from a document",
            "period": "Illustrative sample, not from a document",
        },
        {
            "ticker": "MSFT",
            "name": "Microsoft Corporation",
            "sector": "Cloud & AI Copilot",
            "revenue": "$62.00B",
            "growth": "+18% YoY",
            "margin": "68.4%",
            "trend": "up",
            "badge": "Sample Data (old 2023-24)",
            "source": "Illustrative sample, not from a document",
            "period": "Illustrative sample, not from a document",
        },
        {
            "ticker": "GOOGL",
            "name": "Alphabet Inc.",
            "sector": "Search & Cloud Platform",
            "revenue": "$86.30B",
            "growth": "+13% YoY",
            "margin": "56.5%",
            "trend": "up",
            "badge": "Sample Data (old 2023-24)",
            "source": "Illustrative sample, not from a document",
            "period": "Illustrative sample, not from a document",
        },
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "sector": "Hardware & Services",
            "revenue": "$119.60B",
            "growth": "+2% YoY",
            "margin": "45.9%",
            "trend": "down",
            "badge": "Sample Data (old 2023-24)",
            "source": "Illustrative sample, not from a document",
            "period": "Illustrative sample, not from a document",
        },
    ],
}


@router.get("/{name}")
def get_demo_content(name: str) -> dict[str, Any]:
    """Returns verified sample demonstration datasets with explicit is_sample: true."""
    clean_name = name.strip().lower()
    if clean_name in ("single", "nvda"):
        return SAMPLE_SINGLE_STOCK
    if clean_name in ("compare", "comparison", "dual"):
        return SAMPLE_COMPARISON
    if clean_name in ("coverage", "universe"):
        return SAMPLE_COVERAGE

    raise HTTPException(
        status_code=404,
        detail=f"Demo dataset '{name}' not found. Available: 'single', 'compare', 'coverage'.",
    )
