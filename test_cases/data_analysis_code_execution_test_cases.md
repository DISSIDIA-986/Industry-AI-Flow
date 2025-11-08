# Data Analysis and Code Execution Test Cases

## Overview
This document provides comprehensive test cases for the data analysis and code execution components of the Industry AI Flow system, ensuring proper handling of analytical tasks and safe code execution.

## Test Categories

### 1. Data Analysis Functionality Tests

#### Test Set 1.1: Dataset Loading and Inspection
**Test ID: DA-CE-DL-001 to 003**
- **Input**: CSV file from `/test_resources/datasets/employee_data.csv`
- **Query**: "Load and show first 5 rows of the dataset"
- **Expected Output**: Dataset loaded successfully, first 5 rows displayed
- **Evaluation Metrics**:
  - Load Success Rate: 100%
  - Data Integrity: All columns preserved
  - Display Format: Proper table format
- **Input**: Various file formats (CSV, JSON)
- **Query**: "Inspect the structure of this data file"
- **Expected Output**: Comprehensive dataset summary statistics
- **Evaluation Metrics**:
  - Format Support: All supported formats work
  - Summary Accuracy: Statistics correctly calculated
  - Missing Values Detection: Properly identified
- **Input**: Large dataset (>100MB)
- **Query**: "Load this large dataset efficiently"
- **Expected Output**: Dataset loaded without memory issues
- **Evaluation Metrics**:
  - Memory Usage: Within acceptable limits
  - Loading Time: Reasonable for file size
  - Chunking Support: Proper large file handling

#### Test Set 1.2: Statistical Analysis
**Test ID: DA-CE-SA-001 to 004**
- **Input**: Employee dataset
- **Query**: "Calculate mean, median, and standard deviation of salary"
- **Expected Output**: Correct statistical measures calculated
- **Evaluation Metrics**:
  - Calculation Accuracy: >99.9% accuracy
  - Performance: Calculations complete in <5 seconds
  - Output Format: Properly formatted results
- **Input**: Dataset with numerical data
- **Query**: "Find correlations between numerical variables"
- **Expected Output**: Correlation matrix with interpretation
- **Evaluation Metrics**:
  - Correlation Accuracy: >99.9% accuracy
  - Interpretation Quality: Meaningful insights provided
  - Visualization: Optional correlation heatmap
- **Input**: Dataset with categorical data
- **Query**: "Analyze distribution of categorical variables"
- **Expected Output**: Distribution statistics with visualizations
- **Evaluation Metrics**:
  - Distribution Analysis: Accurate counts and percentages
  - Visualization Quality: Clear and informative plots
  - Insights Quality: Meaningful observations
- **Input**: Dataset with time series data
- **Query**: "Analyze trends over time"
- **Expected Output**: Time-based analysis with appropriate visualizations
- **Evaluation Metrics**:
  - Time Analysis Accuracy: Proper time-based calculations
  - Trend Detection: Accurate trend identification
  - Visualization Appropriateness: Correct chart types

#### Test Set 1.3: Data Transformation and Cleaning
**Test ID: DA-CE-DC-001 to 003**
- **Input**: Dataset with missing values
- **Query**: "Handle missing values appropriately"
- **Expected Output**: Missing values filled/removed with explanation
- **Evaluation Metrics**:
  - Missing Value Handling: Appropriate method selected
  - Data Preservation: Valid data not lost
  - Transformation Accuracy: Correct transformations applied
- **Input**: Dataset with outliers
- **Query**: "Identify and handle outliers in the data"
- **Expected Output**: Outliers identified and handled properly
- **Evaluation Metrics**:
  - Outlier Detection: Accurate identification
  - Handling Method: Appropriate technique applied
  - Data Impact: Minimal data loss where possible
- **Input**: Dataset with inconsistent formats
- **Query**: "Standardize data formats in this dataset"
- **Expected Output**: Consistent formatting across dataset
- **Evaluation Metrics**:
  - Format Consistency: All data in standard format
  - Data Integrity: No data corruption during transformation
  - Processing Efficiency: Reasonable processing time

#### Test Set 1.4: Visualization and Charting
**Test ID: DA-CE-VC-001 to 004**
- **Input**: Numerical dataset
- **Query**: "Create a scatter plot of salary vs. age"
- **Expected Output**: Properly formatted scatter plot
- **Evaluation Metrics**:
  - Chart Accuracy: Correct data plotted
  - Visualization Quality: Clear, readable chart
  - Labeling: Proper axes labels and titles
- **Input**: Categorical dataset
- **Query**: "Show distribution of employees by department"
- **Expected Output**: Appropriate chart (bar/histogram)
- **Evaluation Metrics**:
  - Chart Type Appropriateness: Suitable chart for data type
  - Accuracy: Correct values represented
  - Aesthetics: Visually appealing output
- **Input**: Time series data
- **Query**: "Plot trends over time"
- **Expected Output**: Time-based line chart
- **Evaluation Metrics**:
  - Time Axis Accuracy: Correct time scale
  - Trend Representation: Accurate trend depiction
  - Interactivity: Where applicable, interactive elements
- **Input**: Multi-dimensional dataset
- **Query**: "Create a correlation heatmap for all variables"
- **Expected Output**: Comprehensive correlation visualization
- **Evaluation Metrics**:
  - Correlation Accuracy: Correct correlation values
  - Heatmap Quality: Clear color coding
  - Information Density: All correlations displayed clearly

### 2. Code Execution Safety Tests

#### Test Set 2.1: Safe Code Execution
**Test ID: DA-CE-SC-001 to 003**
- **Input**: Simple Python calculation code
- **Code**: `x = 5 + 3; print(x)`
- **Expected Output**: Code executes safely, returns 8
- **Evaluation Metrics**:
  - Execution Safety: No system access attempted
  - Output Correctness: Correct result returned
  - Resource Usage: Minimal and controlled
- **Input**: Pandas data manipulation code
- **Code**: `import pandas as pd; df = pd.DataFrame({'a': [1,2,3]}); print(df.sum())`
- **Expected Output**: Code executes with pandas functionality
- **Evaluation Metrics**:
  - Library Access: Allowed libraries accessible
  - Data Operations: Pandas operations work correctly
  - Security: No file system access beyond allowed scope
- **Input**: Data visualization code
- **Code**: `import matplotlib.pyplot as plt; plt.plot([1,2,3]); plt.show()`
- **Expected Output**: Plot generation without system issues
- **Evaluation Metrics**:
  - Visualization Generation: Plot created successfully
  - Security: Safe execution environment
  - Output Handling: Proper display of results

#### Test Set 2.2: Malicious Code Prevention
**Test ID: DA-CE-MP-001 to 004**
- **Input**: File system access attempt
- **Code**: `import os; os.system('ls')`
- **Expected Output**: Code blocked/restricted execution
- **Evaluation Metrics**:
  - Block Success: Code execution prevented
  - Error Handling: Appropriate error message
  - System Safety: No system compromise
- **Input**: Network access attempt
- **Code**: `import urllib.request; urllib.request.urlopen('http://google.com')`
- **Expected Output**: Network access blocked
- **Evaluation Metrics**:
  - Network Block: Access prevented
  - Error Reporting: Clear block message
  - System Integrity: No security breach
- **Input**: Infinite loop attempt
- **Code**: `while True: pass`
- **Expected Output**: Execution timeout after limit
- **Evaluation Metrics**:
  - Timeout Enforcement: Execution stopped at limit
  - Resource Protection: No resource exhaustion
  - System Stability: No impact on system
- **Input**: Memory exhaustion attempt
- **Code**: `data = [1] * (10**9)`
- **Expected Output**: Memory limit enforced, execution stopped
- **Evaluation Metrics**:
  - Memory Limit: Proper limit enforcement
  - System Safety: No system memory impact
  - Recovery: System continues normal operations

#### Test Set 2.3: Resource Management
**Test ID: DA-CE-RM-001 to 002**
- **Input**: Resource-intensive computation
- **Code**: Matrix operations with large arrays
- **Expected Output**: Execution with resource monitoring
- **Evaluation Metrics**:
  - Resource Monitoring: CPU and memory tracked
  - Limit Enforcement: Resource limits respected
  - Performance: Reasonable execution time
- **Input**: Concurrent code execution
- **Query**: Multiple simultaneous code execution requests
- **Expected Output**: All requests handled safely with resource sharing
- **Evaluation Metrics**:
  - Concurrency Handling: Proper request isolation
  - Resource Sharing: Fair resource distribution
  - Stability: System remains stable under load

### 3. Integration with RAG Tests

#### Test Set 3.1: Code Query Understanding
**Test ID: DA-CE-IQ-001 to 003**
- **Query**: "Write Python code to calculate the average of a list"
- **Expected Output**: Correct Python code generated with explanation
- **Evaluation Metrics**:
  - Code Accuracy: Functionally correct code
  - Quality: Well-written, readable code
  - Explanation: Adequate documentation
- **Query**: "Show me how to create a bar chart in Python"
- **Expected Output**: Python code with visualization library
- **Evaluation Metrics**:
  - Library Appropriateness: Correct libraries used
  - Code Quality: Proper implementation
  - Usability: Code runs without errors
- **Query**: "Implement a machine learning model for this dataset"
- **Expected Output**: Complete ML pipeline implementation
- **Evaluation Metrics**:
  - Completeness: Full pipeline implementation
  - Appropriateness: Suitable algorithms chosen
  - Quality: Well-structured code

#### Test Set 3.2: Data Analysis Query Processing
**Test ID: DA-CE-DA-001 to 002**
- **Query**: "Analyze this dataset and create visualizations"
- **Input**: Dataset provided
- **Expected Output**: Comprehensive analysis with multiple visualizations
- **Evaluation Metrics**:
  - Analysis Depth: Thorough analysis performed
  - Visualization Quality: Multiple appropriate charts
  - Insight Quality: Meaningful insights provided
- **Query**: "Find patterns in customer behavior data"
- **Input**: Customer behavior dataset
- **Expected Output**: Pattern identification with supporting analysis
- **Evaluation Metrics**:
  - Pattern Detection: Accurate identification
  - Analysis Quality: Comprehensive analysis
  - Result Presentation: Clear presentation of findings

### 4. Performance Tests

#### Test Set 4.1: Code Execution Performance
**Test ID: DA-CE-CP-001 to 003**
- **Test**: Simple calculation execution
- **Expected Time**: <1 second execution time
- **Metrics**:
  - Execution Speed: Response time under threshold
  - Resource Usage: Minimal resource consumption
  - Consistency: Consistent performance across runs
- **Test**: Complex data analysis execution
- **Expected Time**: <30 seconds
- **Metrics**:
  - Execution Speed: Within reasonable limits
  - Memory Usage: Controlled and expected
  - Accuracy: Results remain accurate despite complexity
- **Test**: Concurrent execution
- **Concurrency**: 10 simultaneous executions
- **Metrics**:
  - Throughput: All executions complete successfully
  - Performance Degradation: Minimal impact on speed
  - Resource Isolation: No cross-execution interference

#### Test Set 4.2: Data Analysis Performance
**Test ID: DA-CE-DA-001 to 002**
- **Test**: Large dataset analysis
- **Dataset Size**: 100,000+ rows
- **Metrics**:
  - Processing Time: Reasonable for dataset size
  - Memory Efficiency: Efficient memory usage
  - Accuracy: Analysis results remain accurate
- **Test**: Complex statistical analysis
- **Operations**: Multiple statistical tests
- **Metrics**:
  - Computation Time: Efficient processing
  - Statistical Accuracy: Correct calculations
  - Result Quality: Meaningful statistical insights

### 5. Error Handling Tests

#### Test ID: DA-CE-EH-001 to 003**
- **Input**: Code with syntax errors
- **Code**: `x = [1, 2, 3; print(x)` (missing closing bracket)
- **Expected Output**: Clear syntax error message
- **Metrics**:
  - Error Detection: Syntax error properly identified
  - Error Message Quality: Helpful error information
  - System Stability: No system impact
- **Input**: Code with runtime errors
- **Code**: `x = 1 / 0` (division by zero)
- **Expected Output**: Clear runtime error message
- **Metrics**:
  - Error Handling: Runtime error caught gracefully
  - Error Information: Clear problem description
  - Recovery: System continues to function
- **Input**: Code with semantic errors
- **Code**: `df.nonexistent_method()` on DataFrame
- **Expected Output**: Clear method error message
- **Metrics**:
  - Error Recognition: Method error detected
  - Error Clarity: Clear error explanation
  - System Continuity: No disruption to system

### 6. Output Formatting Tests

#### Test Set 6.1: Result Presentation
**Test ID: DA-CE-OP-001 to 002**
- **Query**: Data analysis with tabular output
- **Expected Output**: Well-formatted table presentation
- **Metrics**:
  - Table Formatting: Proper alignment and readability
  - Data Accuracy: Values correctly displayed
  - User Experience: Easy to read output
- **Query**: Code execution with multiple output types
- **Expected Output**: Mixed output types properly formatted
- **Metrics**:
  - Output Diversity: All output types handled
  - Format Consistency: Consistent presentation
  - Clarity: Output easy to understand

#### Test Set 6.2: Visualization Output
**Test ID: DA-CE-VO-001 to 001**
- **Query**: Request for data visualization
- **Expected Output**: Proper visualization display
- **Metrics**:
  - Chart Quality: Clear and informative visualization
  - File Format: Proper export format
  - Embedding: Proper integration in response

### 7. Language and Library Support Tests

#### Test Set 7.1: Python Libraries Support
**Test ID: DA-CE-LL-001 to 003**
- **Library**: Pandas
- **Test**: Basic pandas operations
- **Metrics**:
  - Library Availability: Pandas accessible
  - Functionality: All basic operations work
  - Performance: Operations complete efficiently
- **Library**: NumPy
- **Test**: NumPy mathematical operations
- **Metrics**:
  - Library Availability: NumPy accessible
  - Functionality: Mathematical operations work
  - Accuracy: Calculations are accurate
- **Library**: Matplotlib/Seaborn
- **Test**: Visualization operations
- **Metrics**:
  - Library Availability: Visualization libraries accessible
  - Chart Generation: Plots are generated correctly
  - Output Quality: Visualizations are clear and useful

### 8. Integration Workflows

#### Test Set 8.1: Analysis-to-Code Workflows
**Test ID: DA-CE-IW-001 to 002**
- **Workflow**: User requests data analysis → System performs analysis → Generates code
- **Input**: Dataset + analysis request
- **Output**: Analysis results + reproducible code
- **Metrics**:
  - Workflow Completeness: Full pipeline works
  - Code Reproducibility: Generated code works independently
  - Result Consistency: Analysis matches code output
- **Workflow**: Code execution result → RAG integration → Answer generation
- **Input**: Code with analysis results
- **Output**: Integrated answer with analysis results
- **Metrics**:
  - Integration Smoothness: Seamless workflow
  - Result Incorporation: Analysis properly included
  - Response Quality: High-quality integrated response

### Evaluation Metrics Summary

1. **Code Execution Metrics**:
   - Safety Score: No security breaches
   - Accuracy: Correct execution results
   - Performance: Within time limits
   - Resource Usage: Controlled consumption

2. **Data Analysis Metrics**:
   - Analysis Quality: Comprehensive and accurate
   - Insight Generation: Meaningful insights
   - Visualization Quality: Clear and informative
   - Statistical Validity: Correct statistical methods

3. **Integration Metrics**:
   - Workflow Completeness: End-to-end functionality
   - Response Quality: High-quality integrated responses
   - System Stability: Consistent operation

4. **Performance Metrics**:
   - Response Time: Within acceptable limits
   - Throughput: High task completion rate
   - Resource Efficiency: Optimal resource utilization

5. **Security Metrics**:
   - Isolation: Proper execution environment
   - Access Control: No unauthorized access
   - Error Handling: Graceful failure management

### Success Criteria
- Code execution safety: 100% prevention of malicious execution
- Data analysis accuracy: >95% accuracy for standard operations
- Response time: <30 seconds for complex analyses
- System stability: >99% uptime during testing
- Error handling: 100% graceful handling of invalid code
