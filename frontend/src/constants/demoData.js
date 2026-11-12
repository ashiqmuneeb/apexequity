/**
 * Instant Demo Pre-Cached Datasets
 * Allows any evaluator or beginner to immediately test the full UI without requiring an API key.
 */

export const DEMO_SINGLE_STOCK = {
  ticker: 'NVDA',
  report: `## Executive Investment Summary: NVIDIA Corporation (NVDA)

### 1. Revenue Trajectory & Operating Momentum
NVIDIA Corporation delivered record-breaking performance in Q4, reporting total quarterly revenue of **$22.10 billion**, representing a staggering **265% year-over-year increase** compared to $6.05 billion in the prior-year period. Full-year revenue surged to unprecedented highs, fueled predominantly by enterprise-wide infrastructure transformations across accelerated computing and generative artificial intelligence.

* **Data Center Dominance:** Data Center segment revenue expanded to **$18.4 billion**, skyrocketing **409% year-over-year**. Hyperscale cloud service providers and enterprise clusters represented over half of all Data Center shipments.
* **Operating Leverage & Margins:** Gross margins expanded to **76.0%**, benefiting from high-margin software stack integration (NVIDIA AI Enterprise, CUDA, TensorRT) alongside massive hardware volume shipment efficiencies.

### 2. Core Technological Drivers & AI Positioning
The primary catalyst behind this unprecedented operating expansion is the global transition from general-purpose CPU computing to **accelerated parallel computing**:

* **Hopper GPU Architecture:** Enterprise adoption of the **H100 Tensor Core GPU** remained virtually unconstrained by demand, with supply chains scaling rapidly across packaging and foundry partners.
* **Networking Integration (Quantum InfiniBand):** InfiniBand networking revenue grew more than threefold YoY, demonstrating that enterprise AI workloads require end-to-end compute-and-fabric synergy rather than standalone accelerators.
* **Software Ecosystem Moat:** The CUDA software layer constitutes an exceptionally defensible competitive moat, with millions of registered developers globally locking enterprise AI stacks to NVIDIA architecture.

### 3. Material Risk Factors & Regulatory Disclosures
* **Geopolitical & Export Restrictions:** Recent revisions to US export controls regarding advanced semiconductor exports to China represent an ongoing headwind. Management noted a steep drop in China Data Center sales, offset by vigorous domestic and European enterprise demand.
* **Foundry & CoWoS Supply Chain Limits:** Ongoing advanced packaging constraints (specifically TSMC Chip-on-Wafer-on-Substrate) dictate maximum potential unit throughput.

### 4. Summary Financial Scorecard
* **Reported Quarterly Revenue:** $22.1 Billion
* **Year-over-Year Growth:** +265%
* **GAAP Gross Margin:** 76.0%
* **Consensus Rating:** Strong Buy / Overweight Moat`,
  metrics: {
    revenue: 22.1,
    revenue_label: '$22.1B',
    growth_yoy: 265,
    growth_label: '+265%',
    gross_margin: 76.0,
    margin_label: '76.0%',
    primary_driver: 'H100 Hopper & AI Enterprise',
  },
  sentiment: 'Strong Growth & Expanding Operating Margins',
  sources: [
    {
      score: 0.942,
      text: 'NVIDIA Corporation (NVDA) reported record Q4 revenue of $22.1 billion, up 265% from a year ago. Growth was driven by massive enterprise demand for H100 Tensor Core GPUs and Hopper architecture. Data Center revenue grew 409% year-over-year. Key risks include export control restrictions and supply chain limits.',
    },
    {
      score: 0.887,
      text: 'Gross margins expanded to 76.0% for the quarter. Strong demand for accelerated computing platforms across cloud providers, enterprise software, and consumer internet companies drove unprecedented operating leverage.',
    },
    {
      score: 0.831,
      text: 'Supply chain constraints for CoWoS packaging remain a key monitorable. Management has engaged secondary and tertiary supply partners to scale throughput into the next fiscal year.',
    },
  ],
};

export const DEMO_COMPARISON = {
  stock_a: 'NVDA',
  stock_b: 'GOOGL',
  report: `## Dual-Issuer Comparative Dossier: NVIDIA ($NVDA) vs. Alphabet ($GOOGL)

### 1. Revenue Momentum & Growth Multiples
* **NVIDIA ($NVDA):** Delivered an astounding **265% YoY revenue growth** to **$22.1B**, powered almost entirely by the accelerated hardware and infrastructure buildout across enterprise and hyperscale customers.
* **Alphabet ($GOOGL):** Reported revenue of **$86.3B**, representing a solid **13% YoY growth rate**, underpinned by durable search advertising demand and accelerating momentum in Google Cloud Platform (GCP).
* **Multiples Comparison:** While Alphabet exhibits a much larger absolute top-line volume ($86.3B vs. $22.1B), NVIDIA commands exponential growth velocity (+265% vs. +13%), commanding higher forward valuation multiples.

### 2. Cloud & Artificial Intelligence Infrastructure Moats
* **NVIDIA Hardware Dominance:** NVIDIA holds a near-monopoly on high-performance training accelerators through Hopper and Blackwell, backed by the CUDA software ecosystem which prevents customer churn.
* **Google Full-Stack Synergy:** Google operates a vertically integrated AI stack—developing custom internal silicon (TPUs), operating hyper-scale cloud infrastructure (GCP), and building foundation models (Gemini) deployed directly across billions of active Android and Workspace users.

### 3. Balance Sheet Resilience & Operating Margins
* **NVIDIA:** Gross margin of **76.0%** highlights extreme pricing power in compute silicon.
* **Alphabet:** Operating margin of **27.5%** reflects stable advertising cash flows that comfortably fund massive ongoing capital expenditures ($32B+ annualized) into data center buildouts.

### 4. Primary Risk Multiples
* **NVIDIA:** Highly concentrated supply chain dependencies (TSMC foundry & packaging) and US export control revisions on China.
* **Alphabet:** Digital advertising cyclical sensitivity and major ongoing Department of Justice antitrust litigation regarding search distribution agreements.`,
  comparison_metrics: [
    { metric: 'Revenue ($B)', NVDA: 22.1, GOOGL: 86.3 },
    { metric: 'YoY Growth (%)', NVDA: 265, GOOGL: 13 },
    { metric: 'Gross Margin (%)', NVDA: 76.0, GOOGL: 56.5 },
  ],
  sources: [
    {
      score: 0.923,
      text: 'NVIDIA Corporation (NVDA) reported record Q4 revenue of $22.1 billion, up 265% from a year ago. Growth was driven by massive enterprise demand for H100 Tensor Core GPUs and Hopper architecture.',
    },
    {
      score: 0.915,
      text: 'Alphabet Inc. (GOOGL) reported Q4 revenue of $86.3 billion, up 13% YoY, propelled by Search and Google Cloud momentum. Google Cloud reached $9.19 billion in revenue with expanding operating margins.',
    },
  ],
};

