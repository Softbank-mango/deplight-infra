import streamlit as st
import math
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Calculator App",
    page_icon="🧮",
    layout="wide"
)

# Custom CSS for dark theme
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    }
    .calculator-title {
        text-align: center;
        color: white;
        font-size: 3rem;
        margin-bottom: 2rem;
    }
    .result-box {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="calculator-title">🧮 Scientific Calculator</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("About")
    st.info("Simple calculator app deployed with Deplight Platform")
    st.markdown("---")
    st.subheader("Features")
    st.markdown("""
    - Basic arithmetic operations
    - Scientific functions
    - Power and root calculations
    - Percentage calculations
    """)
    st.markdown("---")
    st.caption(f"Deployed: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# Main calculator interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Basic Operations")

    # Two numbers input
    num1 = st.number_input("First Number", value=0.0, format="%.4f")
    num2 = st.number_input("Second Number", value=0.0, format="%.4f")

    # Operation selection
    operation = st.selectbox(
        "Select Operation",
        ["Add (+)", "Subtract (-)", "Multiply (×)", "Divide (÷)", "Power (^)", "Modulo (%)"]
    )

    # Calculate button
    if st.button("Calculate", type="primary"):
        try:
            if operation == "Add (+)":
                result = num1 + num2
            elif operation == "Subtract (-)":
                result = num1 - num2
            elif operation == "Multiply (×)":
                result = num1 * num2
            elif operation == "Divide (÷)":
                if num2 == 0:
                    st.error("Error: Division by zero!")
                    result = None
                else:
                    result = num1 / num2
            elif operation == "Power (^)":
                result = num1 ** num2
            elif operation == "Modulo (%)":
                if num2 == 0:
                    st.error("Error: Modulo by zero!")
                    result = None
                else:
                    result = num1 % num2

            if result is not None:
                st.markdown(f'<div class="result-box"><h2>Result: {result:.4f}</h2></div>', unsafe_allow_html=True)
                st.success(f"Calculation completed: {num1} {operation.split()[0]} {num2} = {result:.4f}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    st.subheader("Scientific Functions")

    sci_num = st.number_input("Number for Scientific Operations", value=0.0, format="%.4f")

    sci_operation = st.selectbox(
        "Select Function",
        ["Square Root (√)", "Square (x²)", "Cube (x³)", "Sine (sin)", "Cosine (cos)", "Tangent (tan)", "Natural Log (ln)", "Log Base 10 (log)"]
    )

    if st.button("Compute", type="primary"):
        try:
            if sci_operation == "Square Root (√)":
                if sci_num < 0:
                    st.error("Error: Cannot calculate square root of negative number!")
                else:
                    result = math.sqrt(sci_num)
                    st.success(f"√{sci_num} = {result:.4f}")
            elif sci_operation == "Square (x²)":
                result = sci_num ** 2
                st.success(f"{sci_num}² = {result:.4f}")
            elif sci_operation == "Cube (x³)":
                result = sci_num ** 3
                st.success(f"{sci_num}³ = {result:.4f}")
            elif sci_operation == "Sine (sin)":
                result = math.sin(math.radians(sci_num))
                st.success(f"sin({sci_num}°) = {result:.4f}")
            elif sci_operation == "Cosine (cos)":
                result = math.cos(math.radians(sci_num))
                st.success(f"cos({sci_num}°) = {result:.4f}")
            elif sci_operation == "Tangent (tan)":
                result = math.tan(math.radians(sci_num))
                st.success(f"tan({sci_num}°) = {result:.4f}")
            elif sci_operation == "Natural Log (ln)":
                if sci_num <= 0:
                    st.error("Error: Cannot calculate log of non-positive number!")
                else:
                    result = math.log(sci_num)
                    st.success(f"ln({sci_num}) = {result:.4f}")
            elif sci_operation == "Log Base 10 (log)":
                if sci_num <= 0:
                    st.error("Error: Cannot calculate log of non-positive number!")
                else:
                    result = math.log10(sci_num)
                    st.success(f"log₁₀({sci_num}) = {result:.4f}")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Additional features
st.markdown("---")
st.subheader("Quick Calculations")

col3, col4, col5 = st.columns(3)

with col3:
    st.markdown("**Percentage Calculator**")
    base_value = st.number_input("Base Value", value=100.0, key="pct_base")
    percentage = st.number_input("Percentage (%)", value=10.0, key="pct")
    if st.button("Calculate %"):
        result = (base_value * percentage) / 100
        st.info(f"{percentage}% of {base_value} = {result:.2f}")

with col4:
    st.markdown("**Circle Area**")
    radius = st.number_input("Radius", value=1.0, key="radius")
    if st.button("Calculate Area"):
        area = math.pi * (radius ** 2)
        st.info(f"Area = {area:.4f}")

with col5:
    st.markdown("**Factorial**")
    fact_num = st.number_input("Number (n!)", value=5, min_value=0, max_value=20, step=1, key="factorial")
    if st.button("Calculate n!"):
        result = math.factorial(int(fact_num))
        st.info(f"{fact_num}! = {result}")

# Footer
st.markdown("---")
st.caption("Deployed with ❤️ using Deplight Platform")
