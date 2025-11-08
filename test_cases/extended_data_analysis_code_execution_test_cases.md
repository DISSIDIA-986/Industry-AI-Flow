# Extended Data Analysis and Code Execution Test Cases

## Overview
This document provides extended test cases for the data analysis and code execution components with additional scenarios and edge cases.

## Extended Test Categories

### 1. Extended Data Analysis Functionality Tests

#### Test Set 1.1: Advanced Statistical Analysis
**Test ID: DA-ED-AS-001 to 003**
- **Input**: Employee dataset with salary information
- **Query**: "Perform advanced statistical analysis including skewness, kurtosis, and outlier detection"
- **Expected Output**: Comprehensive statistical report with advanced metrics
- **Evaluation Metrics**:
  - Statistical Accuracy: >99.5% accuracy for calculated metrics
  - Advanced Metrics: All requested statistics calculated correctly
  - Outlier Detection: Proper identification of outliers
- **Dataset**: `/test_resources/datasets/employee_analysis.csv`

- **Input**: Product sales dataset
- **Query**: "Calculate correlation matrix, p-values, and confidence intervals for all numeric variables"
- **Expected Output**: Statistical analysis with significance testing
- **Evaluation Metrics**:
  - Correlation Accuracy: >99.8% accuracy
  - Statistical Test Accuracy: Proper p-values calculated
  - Confidence Interval Accuracy: Correct intervals computed
- **Dataset**: `/test_resources/datasets/product_sales.csv`

- **Input**: Any numerical dataset
- **Query**: "Perform time series decomposition if temporal data is present, otherwise use multivariate analysis"
- **Expected Output**: Appropriate analysis based on data characteristics
- **Evaluation Metrics**:
  - Method Selection: Correct analysis method chosen
  - Decomposition Accuracy: Proper trend/seasonality identification
  - Multivariate Analysis: Appropriate techniques applied

#### Test Set 1.2: Complex Data Transformations
**Test ID: DA-ED-CD-001 to 002**
- **Input**: Dataset with missing values and categorical variables
- **Query**: "Apply advanced imputation techniques (kNN, MICE) and encode categorical variables using target encoding"
- **Expected Output**: Proper data transformations with explained methodology
- **Evaluation Metrics**:
  - Imputation Accuracy: Missing values filled appropriately
  - Encoding Quality: Proper categorical encoding applied
  - Data Integrity: Original relationships maintained

- **Input**: Dataset with skewed distributions
- **Query**: "Apply appropriate transformations (log, Box-Cox) to normalize distributions"
- **Expected Output**: Normalized data with before/after comparisons
- **Evaluation Metrics**:
  - Transformation Appropriateness: Correct transformation method used
  - Normalization Effectiveness: Distributions improved
  - Data Quality: Information preserved during transformation

#### Test Set 1.3: Predictive Modeling
**Test ID: DA-ED-PM-001 to 002**
- **Input**: Employee dataset with features and salary
- **Query**: "Build a predictive model to forecast salary based on experience, education, and department"
- **Expected Output**: Trained model with performance metrics
- **Evaluation Metrics**:
  - Model Training: Successful model training
  - Performance Metrics: RMSE, R², MAE calculated
  - Feature Importance: Proper importance ranking
- **Dataset**: `/test_resources/datasets/employee_analysis.csv`

- **Input**: Product sales dataset
- **Query**: "Create a classification model to predict high/low performers based on price, rating, and reviews"
- **Expected Output**: Classification model with evaluation metrics
- **Evaluation Metrics**:
  - Classification Accuracy: >80% accuracy
  - Model Performance: AUC, precision, recall calculated
  - Feature Selection: Relevant features identified

### 2. Extended Code Execution Safety Tests

#### Test Set 2.1: Resource Limit Enforcement
**Test ID: DA-ED-RL-001 to 003**
- **Input**: Memory-intensive code (large matrix operations)
- **Code**: Create large arrays that approach memory limits
- **Expected Output**: Execution completes within limits or is terminated
- **Evaluation Metrics**:
  - Memory Limiting: Proper memory constraints enforced
  - Graceful Termination: No system crashes
  - Error Reporting: Clear memory limit exceeded message

- **Input**: CPU-intensive computation
- **Code**: Intensive numerical computation approaching time limits
- **Expected Output**: Execution completes within time limits or is terminated
- **Evaluation Metrics**:
  - Time Limiting: Proper time constraints enforced
  - System Stability: No system degradation
  - Process Isolation: Other processes unaffected

- **Input**: File system access attempt beyond allowed scope
- **Code**: Attempt to access system files outside allowed directories
- **Expected Output**: Access blocked with appropriate error
- **Evaluation Metrics**:
  - Access Control: Unauthorized access prevented
  - Error Handling: Proper error messages
  - System Security: No security compromise

#### Test Set 2.2: Complex Code Execution
**Test ID: DA-ED-CC-001 to 002**
- **Input**: Multi-file code execution
- **Code**: Code that references external modules and imports
- **Expected Output**: Proper execution with all dependencies
- **Evaluation Metrics**:
  - Import Handling: Allowed modules accessible
  - Dependency Management: Proper module resolution
  - Execution Completeness: Code completes as expected

- **Input**: Code with error handling and exception management
- **Code**: Code with try-catch blocks and custom error handling
- **Expected Output**: Proper error handling without system issues
- **Evaluation Metrics**:
  - Exception Handling: Errors handled gracefully
  - Error Reporting: Clear exception information
  - System Stability: No system impact from exceptions

### 3. Extended Data Analysis Integration Tests

#### Test Set 3.1: Cross-Dataset Analysis
**Test ID: DA-ED-XD-001 to 001**
- **Query**: "Merge employee and salary data, then analyze compensation by department and experience level"
- **Input**: Multiple datasets (employee_analysis.csv and salary data)
- **Expected Output**: Properly merged analysis with insights
- **Evaluation Metrics**:
  - Data Merging: Accurate dataset combination
  - Analysis Quality: Meaningful cross-dataset insights
  - Performance: Efficient processing of multiple datasets
- **Datasets**: `/test_resources/datasets/employee_analysis.csv`, `/test_resources/datasets/other_salary_data.csv` (if available)

#### Test Set 3.2: Advanced Visualization
**Test ID: DA-ED-AV-001 to 002**
- **Query**: "Create advanced visualizations: heatmap with clustering, 3D scatter plot, and interactive dashboard elements"
- **Input**: Multi-dimensional dataset
- **Expected Output**: Complex visualizations with advanced features
- **Evaluation Metrics**:
  - Visualization Quality: High-quality complex plots
  - Feature Implementation: Advanced visualization features work
  - Output Format: Proper visualization formats generated

- **Query**: "Generate statistical visualizations with confidence intervals and prediction bands"
- **Input**: Dataset suitable for statistical analysis
- **Expected Output**: Statistical plots with uncertainty visualization
- **Evaluation Metrics**:
  - Statistical Accuracy: Correct confidence intervals
  - Visualization Clarity: Uncertainty clearly depicted
  - Graphical Quality: Professional-quality output

### 4. Extended Performance Tests

#### Test ID: DA-ED-EP-001 to 003**
- **Test**: Large dataset analysis
- **Dataset Size**: >100K rows
- **Metrics**:
  - Processing Time: Completion within reasonable time
  - Memory Efficiency: Efficient memory usage
  - Result Accuracy: Analysis remains accurate at scale

- **Test**: Complex multi-step analysis
- **Operations**: 10+ sequential analytical operations
- **Metrics**:
  - Computational Accuracy: Accuracy maintained through all steps
  - Time Complexity: Reasonable processing time
  - Pipeline Integrity: No errors propagate through pipeline

- **Test**: Concurrent analysis requests
- **Concurrency**: 20 simultaneous analysis requests
- **Metrics**:
  - Throughput: All requests processed successfully
  - Performance Isolation: Requests don't affect each other
  - Resource Management: Fair resource allocation

### 5. Extended Error Handling Tests

#### Test Set 5.1: Complex Error Scenarios
**Test ID: DA-ED-CE-001 to 003**
- **Input**: Dataset with complex data quality issues
- **Code**: `df.with_complex_issues = [NaN, "text", 0, -999, ""]`
- **Query**: "Clean and analyze this problematic dataset"
- **Expected Output**: Proper handling of complex data issues
- **Metrics**:
  - Data Cleaning: Issues identified and properly handled
  - Error Recovery: System recovers from data problems
  - Quality Reporting: Clear data quality information

- **Input**: Mismatched data types
- **Code**: Mixed data types in numeric columns
- **Query**: "Convert and analyze this mixed-type dataset"
- **Expected Output**: Proper type conversion and analysis
- **Metrics**:
  - Type Handling: Proper data type conversion
  - Analysis Continuity: Analysis completes despite type issues
  - Warning Generation: Appropriate warnings for conversions

- **Input**: Dataset with structural inconsistencies
- **Code**: Inconsistent column names, missing columns in some rows
- **Query**: "Normalize and analyze this inconsistent dataset"
- **Expected Output**: Proper structuring and analysis
- **Metrics**:
  - Data Normalization: Structure properly normalized
  - Analysis Quality: Valid analysis on normalized data
  - Error Tolerance: Inconsistencies properly handled

### 6. Extended Output Formatting Tests

#### Test Set 6.1: Complex Output Formats
**Test ID: DA-ED-CO-001 to 002**
- **Query**: "Generate analysis report in multiple formats: JSON, CSV, and HTML"
- **Expected Output**: Same analysis in multiple formats
- **Metrics**:
  - Format Accuracy: All formats contain correct data
  - Consistency: Analysis consistent across formats
  - Quality: Professional formatting in all outputs

- **Query**: "Create interactive visualization suitable for web embedding"
- **Expected Output**: Interactive, web-ready visualization
- **Metrics**:
  - Interactivity: Visualization has interactive elements
  - Web Readiness: Proper format for web embedding
  - Functionality: All interactive features work correctly

### 7. Extended Data Type Tests

#### Test Set 7.1: Specialized Data Formats
**Test ID: DA-ED-SD-001 to 002**
- **Input**: Time series data
- **Query**: "Analyze trends, seasonality, and anomalies in this time series"
- **Expected Output**: Time series specific analysis
- **Metrics**:
  - Time Series Recognition: Correctly identified as time series
  - Analysis Appropriateness: Time series methods applied
  - Pattern Detection: Trends and seasonality identified

- **Input**: Geographic data
- **Query**: "If geographic data present, create maps and spatial analysis"
- **Expected Output**: Geographic visualization and analysis
- **Metrics**:
  - Geographic Recognition: Geographic data identified
  - Spatial Analysis: Appropriate spatial methods applied
  - Mapping Quality: Quality maps generated

### 8. Extended Library Support Tests

#### Test Set 8.1: Advanced Library Functions
**Test ID: DA-ED-AL-001 to 003**
- **Library**: Scikit-learn
- **Test**: Advanced ML algorithms (Random Forest, XGBoost, etc.)
- **Metrics**:
  - Algorithm Availability: Advanced algorithms accessible
  - Performance: Algorithms execute efficiently
  - Result Quality: High-quality model results

- **Library**: Statsmodels
- **Test**: Advanced statistical modeling
- **Metrics**:
  - Statistical Model Availability: Advanced models accessible
  - Statistical Accuracy: Models calculated correctly
  - Diagnostic Quality: Proper statistical diagnostics

- **Library**: Plotly/Bokeh
- **Test**: Interactive visualization creation
- **Metrics**:
  - Visualization Availability: Interactive charts accessible
  - Interactivity Quality: Interactive features work properly
  - Output Quality: High-quality interactive charts

### 9. Extended Integration Workflows

#### Test Set 9.1: Advanced Multi-Step Workflows
**Test ID: DA-ED-AM-001 to 001**
- **Workflow**: Data loading → cleaning → feature engineering → modeling → validation → visualization
- **Input**: Raw dataset requiring comprehensive processing
- **Output**: Complete analytical workflow execution
- **Metrics**:
  - Workflow Completion: All steps execute successfully
  - Error Propagation: Errors handled properly across steps
  - Quality Maintenance: Quality maintained throughout workflow

### 10. Extended Real-World Scenario Tests

#### Test Set 10.1: Business Intelligence Scenarios
**Test ID: DA-ED-BI-001 to 002**
- **Scenario**: "As a business analyst, I need to understand which products are underperforming and why"
- **Input**: Product sales dataset
- **Expected**: Comprehensive business analysis with actionable insights
- **Metrics**:
  - Business Insight Quality: Actionable business insights provided
  - Analysis Depth: Comprehensive analysis performed
  - Recommendation Quality: Valid business recommendations
- **Dataset**: `/test_resources/datasets/product_sales.csv`

- **Scenario**: "As an HR director, I need to analyze compensation equity and identify areas for adjustment"
- **Input**: Employee dataset
- **Expected**: HR-focused analysis with equity assessment
- **Metrics**:
  - Domain Focus: HR-specific analysis performed
  - Equity Analysis: Proper equity measures calculated
  - Recommendation Quality: Valid HR recommendations
- **Dataset**: `/test_resources/datasets/employee_analysis.csv`

#### Test Set 10.2: Scientific Analysis Scenarios
**Test ID: DA-ED-SA-001 to 001**
- **Scenario**: "I need to conduct a statistical significance test to determine if there are meaningful differences between groups"
- **Input**: Dataset with grouping variables
- **Expected**: Proper statistical testing with significance assessment
- **Metrics**:
  - Statistical Test Appropriateness: Correct statistical test chosen
  - P-value Accuracy: Correct p-values calculated
  - Significance Assessment: Proper significance interpretation

## Extended Evaluation Metrics Summary

1. **Statistical Analysis Quality**: Accuracy of advanced statistical methods
2. **Machine Learning Integration**: Quality of predictive modeling
3. **Resource Management**: Proper enforcement of limits
4. **Data Quality Handling**: Ability to handle complex data issues
5. **Performance at Scale**: Efficiency with large datasets
6. **Cross-Dataset Analysis**: Ability to work with multiple datasets
7. **Advanced Visualization**: Quality of complex visualizations
8. **Real-World Scenario Handling**: Appropriateness for practical applications
9. **Library Integration**: Effectiveness of advanced library usage
10. **Workflow Completeness**: Success in multi-step analyses

## Extended Success Criteria
- Statistical analysis accuracy: >99%
- Machine learning model quality: >85% for basic models
- Resource limit enforcement: 100% effective
- Complex data handling: >90% success rate
- Performance efficiency: <30 seconds for 10K row datasets
- Cross-dataset analysis: >85% success rate
- Advanced visualization quality: >90% functional and accurate
- Real-world scenario appropriateness: >95% relevant
- Library function accessibility: >95% success rate
- Multi-step workflow completion: >90% success rate
