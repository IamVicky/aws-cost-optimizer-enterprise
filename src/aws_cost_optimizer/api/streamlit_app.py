import os
import duckdb
import streamlit as st

from aws_cost_optimizer.config import DUCKDB_PATH
from aws_cost_optimizer.ingest import ingest_data
from aws_cost_optimizer.analysis import QueryAgent, WasteAnalyzer
from aws_cost_optimizer.iac import IaCGenerator
from aws_cost_optimizer.connectors import AWSNonProdConnector, load_accounts_config

# Page Configuration
st.set_page_config(
    page_title="CloudIntel — Enterprise AI FinOps Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .card-approved {
        background-color: #F0FDF4;
        border-left: 5px solid #16A34A;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .card-rejected {
        background-color: #FEF2F2;
        border-left: 5px solid #DC2626;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .badge-pass {
        background-color: #DCFCE7;
        color: #15803D;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-fail {
        background-color: #FEE2E2;
        color: #B91C1C;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper Data Functions
@st.cache_resource
def get_query_agent():
    return QueryAgent()

@st.cache_resource
def get_waste_analyzer():
    return WasteAnalyzer()

@st.cache_resource
def get_iac_generator():
    return IaCGenerator()

def load_recommendations():
    if not os.path.exists(DUCKDB_PATH):
        ingest_data()
        analyzer = get_waste_analyzer()
        analyzer.run_analysis()

    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        df_recs = con.execute("SELECT * FROM candidate_recommendations;").fetchdf()
    except Exception:
        con.close()
        analyzer = get_waste_analyzer()
        analyzer.run_analysis()
        con = duckdb.connect(DUCKDB_PATH, read_only=True)
        df_recs = con.execute("SELECT * FROM candidate_recommendations;").fetchdf()
    con.close()
    return df_recs

# Header
st.markdown('<div class="main-header">⚡ CloudIntel — Enterprise AI FinOps Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Service FinOps Intelligence (ECS, Lambda, S3) with Banking Compliance Guardrails & CloudFormation Studio</div>', unsafe_allow_html=True)

# Sidebar Controls
st.sidebar.title("⚙️ System Controls")
st.sidebar.markdown("---")

# 1. AWS Account Selector (Loaded from accounts config)
accounts_list = load_accounts_config()
account_options = ["All Accounts"] + [f"{a['account_name']} ({a['account_id']})" for a in accounts_list]
selected_account_str = st.sidebar.selectbox("Select Target AWS Account:", options=account_options)

# 2. AWS Authentication Status
connector = AWSNonProdConnector()
aws_authed = connector.is_aws_authenticated()
if aws_authed:
    st.sidebar.success("✓ AWS Access Keys Active")
else:
    st.sidebar.info("ℹ️ Offline / Synthetic Data Mode")

st.sidebar.markdown("---")
st.sidebar.markdown("**🤖 AI Engine**: `Groq API (llama-3.3-70b)`")
st.sidebar.markdown("**💾 Analytical DB**: `DuckDB (cloudintel.duckdb)`")
st.sidebar.markdown("---")

bu_filter = st.sidebar.selectbox(
    "Filter by Business Unit (BU):",
    options=["All Business Units", "Marketing", "Engineering", "DataScience"]
)

guardrails_toggle = st.sidebar.toggle("Enforce Banking Guardrails", value=True, help="When active, rejects unsafe recommendations like removing KMS keys.")

st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Data Pipeline Operations")
if st.sidebar.button("Run ETL Ingestion Pipeline"):
    with st.spinner("Executing ETL ingestion..."):
        ingest_data(use_aws_live=aws_authed)
        st.sidebar.success("ETL completed successfully!")

if st.sidebar.button("Run Waste Analyzer"):
    with st.spinner("Scanning for waste..."):
        analyzer = get_waste_analyzer()
        analyzer.run_analysis()
        st.sidebar.success("Waste analysis updated!")

# Load Data
df_recs_all = load_recommendations()

# Apply BU Filter
if bu_filter != "All Business Units":
    df_recs = df_recs_all[df_recs_all["business_unit"] == bu_filter]
else:
    df_recs = df_recs_all

# Main Application Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Chat Assistant (Text-to-SQL)",
    "📊 Proactive Savings Dashboard",
    "🛡️ Compliance & Guardrail Audit Log",
    "🏗️ Remediation & CloudFormation Studio"
])

# ---------------------------------------------------------
# TAB 1: Chat Assistant (Text-to-SQL + Synthesis)
# ---------------------------------------------------------
with tab1:
    st.subheader("Natural Language FinOps Assistant")
    st.caption("Ask questions about cloud costs, compute utilization, serverless execution, and storage lifecycle.")

    st.markdown("**Sample Prompt Shortcuts:**")
    col1, col2, col3 = st.columns(3)
    sample_prompt = None
    if col1.button("Show top 5 most expensive Lambda functions"):
        sample_prompt = "Show me top 5 most expensive Lambda functions across BUs"
    if col2.button("Which S3 buckets lack lifecycle policies?"):
        sample_prompt = "Which S3 buckets are missing lifecycle policies?"
    if col3.button("Show over-provisioned ECS containers"):
        sample_prompt = "Show over-provisioned ECS task definitions with low CPU utilization"

    user_input = st.text_input("Enter your natural language cost question:", value=sample_prompt if sample_prompt else "", placeholder="e.g. Why did Marketing Lambda & S3 costs spike?")

    if user_input:
        with st.spinner("Processing natural language query..."):
            agent = get_query_agent()
            res = agent.process_query(user_input)

            if res["error"]:
                st.error(f"❌ {res['error']}")
            else:
                st.markdown("### 💡 Executive Insights & Context Explanation")
                st.info(res["explanation"])

                with st.expander("🔍 View Generated SQL Query & Raw Analytical Results"):
                    st.code(res["sql_query"], language="sql")
                    if not res["data"].empty:
                        st.dataframe(res["data"], use_container_width=True)
                    else:
                        st.write("No matching database rows.")

# ---------------------------------------------------------
# TAB 2: Proactive Savings Dashboard
# ---------------------------------------------------------
with tab2:
    st.subheader("Proactive Waste & Savings Opportunities")

    df_approved = df_recs[df_recs["compliance_status"] == "APPROVED"]
    df_rejected = df_recs[df_recs["compliance_status"] != "APPROVED"]

    total_savings = df_approved["estimated_monthly_savings"].sum()
    pass_rate = round((len(df_approved) / len(df_recs) * 100), 1) if len(df_recs) > 0 else 100

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Est. Monthly Savings ($)", f"${total_savings:,.2f}")
    col_m2.metric("Approved Optimizations", f"{len(df_approved)}")
    col_m3.metric("Banking Guardrail Pass Rate", f"{pass_rate}%")

    st.markdown("---")
    st.markdown("### Approved Cost-Saving Recommendation Cards")

    if df_approved.empty:
        st.write("No approved recommendations match current filters.")
    else:
        for idx, row in df_approved.iterrows():
            st.markdown(f"""
            <div class="card-approved">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.1rem; font-weight:700; color:#166534;">{row['recommendation_id']} — {row['service_type']} ({row['business_unit']})</span>
                    <span class="badge-pass">✓ BANKING COMPLIANCE PASSED</span>
                </div>
                <p style="margin-top:0.5rem; color:#1F2937;"><b>Proposed Optimization:</b> {row['proposed_fix_description']}</p>
                <div style="display:flex; justify-content:space-between; margin-top:0.8rem; font-size:0.95rem;">
                    <span><b>Resource ID:</b> <code>{row['resource_id']}</code></span>
                    <span style="font-size:1.1rem; font-weight:700; color:#15803D;">Est. Savings: ${row['estimated_monthly_savings']:,.2f}/mo</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 3: Compliance & Guardrail Audit Log
# ---------------------------------------------------------
with tab3:
    st.subheader("Banking Security & Compliance Policy Interceptor Log")
    st.caption("Transparent audit trail of candidate recommendations rejected by the Banking Guardrails Engine.")

    df_rejected = df_recs[df_recs["compliance_status"] != "APPROVED"]

    if df_rejected.empty:
        st.success("✓ Zero policy violations! All candidate recommendations pass banking compliance guardrails.")
    else:
        for idx, row in df_rejected.iterrows():
            st.markdown(f"""
            <div class="card-rejected">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.1rem; font-weight:700; color:#991B1B;">{row['recommendation_id']} — {row['service_type']} ({row['business_unit']})</span>
                    <span class="badge-fail">⛔ REJECTED: {row['compliance_status']}</span>
                </div>
                <p style="margin-top:0.5rem; color:#1F2937;"><b>Attempted Candidate Fix:</b> {row['proposed_fix_description']}</p>
                <div style="display:flex; justify-content:space-between; margin-top:0.8rem; font-size:0.95rem;">
                    <span><b>Guardrail Rule Triggered:</b> <code>{row['guardrail_rule_triggered']}</code></span>
                    <span style="color:#991B1B; font-weight:600;">Status: Intercepted & Blocked</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 4: Remediation & CloudFormation Studio
# ---------------------------------------------------------
with tab4:
    st.subheader("AWS CloudFormation & Service Catalog Remediation Studio")
    st.caption("Select an approved recommendation to generate compliant AWS CloudFormation YAML code ready for AWS Service Catalog.")

    df_approved = df_recs[df_recs["compliance_status"] == "APPROVED"]

    if df_approved.empty:
        st.warning("No approved recommendations available for CloudFormation generation.")
    else:
        rec_options = [f"{r['recommendation_id']} — {r['service_type']} ({r['business_unit']})" for idx, r in df_approved.iterrows()]
        selected_option = st.selectbox("Select Approved Recommendation:", options=rec_options)

        selected_id = selected_option.split(" — ")[0]
        selected_rec = df_approved[df_approved["recommendation_id"] == selected_id].iloc[0].to_dict()

        if st.button("Generate CloudFormation Remediation Code"):
            with st.spinner("Generating guardrail-checked AWS CloudFormation YAML template..."):
                generator = get_iac_generator()
                cfn_yaml = generator.generate_cloudformation(selected_rec)
                sc_json = generator.generate_service_catalog_product_json(selected_rec, cfn_yaml)

                st.markdown("### 📄 Generated AWS CloudFormation Template (`cloudformation_template.yaml`)")
                st.code(cfn_yaml, language="yaml")
                st.download_button(
                    label="Download CloudFormation YAML",
                    data=cfn_yaml,
                    file_name=f"{selected_id}_cloudformation.yaml",
                    mime="text/yaml"
                )

                st.markdown("---")
                st.markdown("### 📦 AWS Service Catalog Product Definition (`service_catalog_product.json`)")
                st.code(sc_json, language="json")
                st.download_button(
                    label="Download Service Catalog JSON Metadata",
                    data=sc_json,
                    file_name=f"{selected_id}_service_catalog_product.json",
                    mime="application/json"
                )
