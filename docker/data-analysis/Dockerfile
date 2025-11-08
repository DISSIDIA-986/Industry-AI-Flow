# ===================================================================
# Industry AI Flow - Data Analysis Sandbox Docker Image
# ===================================================================
# Purpose: Secure execution environment for Python data analysis code
# Features: Pre-installed libraries, resource limits, network isolation
# ===================================================================

FROM python:3.12-slim

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python data analysis libraries
RUN pip install --no-cache-dir \
    pandas>=2.1.0 \
    numpy>=1.26.4 \
    scipy>=1.11.0 \
    scikit-learn>=1.5.2 \
    xgboost>=2.0.3 \
    lightgbm>=4.3.0 \
    matplotlib>=3.8.0 \
    seaborn>=0.13.1 \
    plotly>=5.17.0 \
    openpyxl>=3.1.2 \
    xlrd>=2.0.1 \
    sqlalchemy>=2.0.0 \
    psycopg2-binary>=2.9.9

# Create non-root user for security
RUN useradd -m -u 1000 sandbox && \
    chown -R sandbox:sandbox /workspace

# Switch to non-root user
USER sandbox

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    OMP_NUM_THREADS=1

# Default command
CMD ["/bin/bash"]
