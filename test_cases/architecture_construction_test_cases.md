# Architecture and Construction Industry Test Cases

## Overview
This document provides comprehensive test cases specifically designed for the architecture and construction industry to validate the RAG system's performance in this domain. The tests cover building codes, structural analysis, project management, sustainability, and design assistance.

## Test Categories

### 1. Building Codes and Compliance Tests

#### Test Set 1.1: International Building Code (IBC) Compliance
**Test ID: AC-BC-IBC-001 to 003**
- **Query**: "What are the fire resistance requirements for high-rise residential buildings according to IBC 2021?"
- **Expected Output**: Specific fire resistance ratings, compartmentalization requirements, egress requirements
- **Domain**: Building Codes
- **Complexity**: High
- **Evaluation Metrics**:
  - Accuracy: >90% of code references correct
  - Completeness: All relevant requirements included
  - Interpretation: Proper interpretation of code language

- **Query**: "How do IBC requirements differ for sprinkler systems in commercial vs residential buildings?"
- **Expected Output**: Specific section numbers, requirements, and differences
- **Domain**: Building Codes
- **Complexity**: High
- **Evaluation Metrics**:
  - Comparative Analysis: Accurate differences identified
  - Code References: Proper section citations
  - Practical Application: Clear implementation guidance

- **Query**: "What are the IBC requirements for seismic design categories in California?"
- **Expected Output**: Seismic design categories, applicable requirements, special provisions
- **Domain**: Building Codes
- **Complexity**: High
- **Evaluation Metrics**:
  - Technical Accuracy: Seismic requirements correct
  - Regional Specifics: California-specific requirements included
  - Structural Implications: Proper structural design requirements

#### Test Set 1.2: Americans with Disabilities Act (ADA) Compliance
**Test ID: AC-BC-ADA-001 to 002**
- **Query**: "What are the ADA requirements for accessible parking spaces in a new commercial facility?"
- **Expected Output**: Number, dimensions, and placement requirements for accessible parking
- **Domain**: Building Codes
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Requirement Accuracy: All ADA requirements correct
  - Calculation Accuracy: Proper ratios and numbers
  - Accessibility Focus: Focus on user experience

- **Query**: "How do I design an accessible route through a building according to ADA standards?"
- **Expected Output**: Path requirements, width, slope, and obstacle specifications
- **Domain**: Building Codes
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Route Planning: Accurate path requirements
  - Dimension Accuracy: Proper measurements and tolerances
  - Barrier-Free Design: Proper accessibility concepts

#### Test Set 1.3: Energy Code Compliance
**Test ID: AC-BC-E-001 to 002**
- **Query**: "What are the energy efficiency requirements for residential buildings under IECC 2021?"
- **Expected Output**: Insulation values, window performance, HVAC efficiency requirements
- **Domain**: Building Codes
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Technical Specifications: Accurate R-values and performance metrics
  - Climate Zone Considerations: Proper regional variations
  - Compliance Pathways: Multiple compliance options if available

- **Query**: "How do ASHRAE 90.1 requirements impact commercial building design?"
- **Expected Output**: Building envelope, lighting, and HVAC system requirements
- **Domain**: Building Codes
- **Complexity**: High
- **Evaluation Metrics**:
  - System Requirements: Accurate technical specifications
  - Performance Metrics: Proper efficiency ratings
  - Cost Implications: Understanding of additional costs

### 2. Structural Analysis Tests

#### Test Set 2.1: Load Analysis
**Test ID: AC-SA-LA-001 to 003**
- **Query**: "Calculate the dead, live, and wind loads on a 12-story office building in Chicago according to ASCE 7-22"
- **Expected Output**: Detailed load calculations with reference to specific ASCE sections
- **Domain**: Structural Engineering
- **Complexity**: High
- **Evaluation Metrics**:
  - Calculation Accuracy: Correct load values
  - Code Compliance: Proper ASCE 7-22 application
  - Regional Factors: Chicago-specific requirements included

- **Query**: "How do I determine the seismic forces for a structure in seismic zone D?"
- **Expected Output**: Seismic parameters, design spectrum, force calculations
- **Domain**: Structural Engineering
- **Complexity**: High
- **Evaluation Metrics**:
  - Seismic Parameters: Correct coefficients and factors
  - Analysis Method: Proper structural analysis approach
  - Code Applications: Correct building code application

- **Query**: "Compare the load-bearing capacity of steel vs concrete columns of the same dimensions"
- **Expected Output**: Capacity calculations with material properties and assumptions
- **Domain**: Structural Engineering
- **Complexity**: High
- **Required Data**: `/test_resources/datasets/construction_materials_properties.csv`
- **Evaluation Metrics**:
  - Material Properties: Accurate material properties used
  - Calculation Accuracy: Correct capacity calculations
  - Comparative Analysis: Fair comparison methodology

#### Test Set 2.2: Material Performance
**Test ID: AC-SA-MP-001 to 002**
- **Query**: "Analyze the deflection of a 10-meter steel beam under a 20 kN/m load"
- **Expected Output**: Deflection calculations with appropriate safety factors
- **Domain**: Structural Engineering
- **Complexity**: High
- **Required Data**: `/test_resources/datasets/construction_materials_properties.csv`
- **Evaluation Metrics**:
  - Calculation Accuracy: Correct deflection formulas
  - Safety Factors: Appropriate factors of safety applied
  - Code Compliance: Deflection limits checked

- **Query**: "What is the maximum span for a timber beam with a given load?"
- **Expected Output**: Span calculations based on timber properties and loading
- **Domain**: Structural Engineering
- **Complexity**: Medium
- **Required Data**: `/test_resources/datasets/construction_materials_properties.csv`
- **Evaluation Metrics**:
  - Material Properties: Correct timber properties used
  - Calculation Method: Appropriate engineering method
  - Safety Factors: Proper limits applied

### 3. Project Management Tests

#### Test Set 3.1: Construction Scheduling
**Test ID: AC-PM-CS-001 to 003**
- **Query**: "What is the typical construction duration for a 25-story mixed-use building?"
- **Expected Output**: Time estimates with factors affecting duration
- **Domain**: Construction Management
- **Complexity**: Medium
- **Required Data**: `/test_resources/datasets/architecture_building_projects.csv`
- **Evaluation Metrics**:
  - Duration Accuracy: Reasonable time estimates
  - Factor Consideration: Relevant factors mentioned
  - Comparison Base: Based on similar projects

- **Query**: "How do weather conditions affect construction schedules in northern climates?"
- **Expected Output**: Weather impact on different phases and activities
- **Domain**: Construction Management
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Phase Impact: Different impacts by construction phase
  - Mitigation Strategies: Ways to reduce weather impact
  - Seasonal Planning: Seasonal scheduling considerations

- **Query**: "What are the critical path activities for a high-rise residential project?"
- **Expected Output**: Key activities and their interdependencies
- **Domain**: Construction Management
- **Complexity**: High
- **Evaluation Metrics**:
  - Critical Activities: Accurate identification of critical activities
  - Dependencies: Clear activity interdependencies
  - Risk Mitigation: Ways to manage critical path risks

#### Test Set 3.2: Cost Estimation
**Test ID: AC-PM-CE-001 to 002**
- **Query**: "Estimate the cost per square foot for a Class A office building in downtown Chicago"
- **Expected Output**: Cost estimate with breakdown and market factors
- **Domain**: Construction Economics
- **Complexity**: High
- **Required Data**: `/test_resources/datasets/architecture_building_projects.csv`
- **Evaluation Metrics**:
  - Cost Accuracy: Reasonable cost estimates
  - Market Factors: Local market considerations
  - Building Class Factors: Class A building characteristics

- **Query**: "Analyze how building height affects construction costs per square foot"
- **Expected Output**: Cost relationships with height and structural requirements
- **Domain**: Construction Economics
- **Complexity**: High
- **Required Data**: `/test_resources/datasets/architecture_building_projects.csv`
- **Evaluation Metrics**:
  - Trend Analysis: Accurate cost-height relationships
  - Structural Impact: Structural cost impacts
  - Efficiency Factors: Economies of scale considerations

### 4. Sustainable Design Tests

#### Test Set 4.1: Energy Performance
**Test ID: AC-SD-EP-001 to 003**
- **Query**: "How does building orientation affect energy consumption?"
- **Expected Output**: Orientation impacts on heating, cooling, and daylighting
- **Domain**: Sustainable Design
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Energy Impacts: Accurate energy effect descriptions
  - Geographic Factors: Climate-specific considerations
  - Design Strategies: Optimal orientation strategies

- **Query**: "What are the most effective strategies for achieving LEED Gold certification?"
- **Expected Output**: Specific LEED strategies by category
- **Domain**: Sustainable Design
- **Complexity**: High
- **Evaluation Metrics**:
  - LEED Knowledge: Accurate LEED credit knowledge
  - Strategy Priority: High-impact strategy prioritization
  - Implementation: Practical implementation methods

- **Query**: "Compare the lifecycle costs of different HVAC systems for a commercial building"
- **Expected Output**: Initial, operational, and maintenance costs
- **Domain**: Sustainable Design
- **Complexity**: High
- **Evaluation Metrics**:
  - Cost Components: All lifecycle cost components included
  - Comparison Basis: Fair comparison methodology
  - Performance Factors: Energy performance included

#### Test Set 4.2: Material Sustainability
**Test ID: AC-SD-MS-001 to 002**
- **Query**: "Which insulation materials have the lowest environmental impact?"
- **Expected Output**: Environmental impact comparison with performance metrics
- **Domain**: Sustainable Design
- **Complexity**: Medium
- **Required Data**: `/test_resources/datasets/construction_materials_properties.csv`
- **Evaluation Metrics**:
  - Environmental Impact: Accurate environmental impact data
  - Performance Balance: Performance vs sustainability tradeoffs
  - Life Cycle Analysis: Full life cycle considerations

- **Query**: "How can I minimize the carbon footprint of concrete in a large project?"
- **Expected Output**: Concrete mix strategies and alternatives
- **Domain**: Sustainable Design
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Carbon Reduction: Effective carbon reduction strategies
  - Performance Impact: Structural performance maintained
  - Practical Implementation: Feasible implementation methods

### 5. Design Assistance Tests

#### Test Set 5.1: Architectural Design
**Test ID: AC-DA-AD-001 to 003**
- **Query**: "What are the design considerations for natural ventilation in residential buildings?"
- **Expected Output**: Ventilation strategies, design features, climate considerations
- **Domain**: Architectural Design
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Design Strategies: Effective natural ventilation strategies
  - Climate Considerations: Climate-appropriate designs
  - Architectural Integration: Design integration approaches

- **Query**: "How do I design a space to meet both acoustic and aesthetic requirements?"
- **Expected Output**: Materials, configurations, and design strategies
- **Domain**: Architectural Design
- **Complexity**: High
- **Evaluation Metrics**:
  - Acoustic Performance: Proper acoustic principles
  - Aesthetic Integration: Aesthetically pleasing solutions
  - Material Solutions: Appropriate material selections

- **Query**: "What are the current trends in multi-family housing design?"
- **Expected Output**: Design trends, resident preferences, market factors
- **Domain**: Architectural Design
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Current Trends: Up-to-date trend information
  - Market Drivers: Understanding of market forces
  - Design Application: Practical design applications

#### Test Set 5.2: Space Planning
**Test ID: AC-DA-SP-001 to 002**
- **Query**: "What are the recommended square footages for different types of office spaces?"
- **Expected Output**: Space requirements by function and density
- **Domain**: Architectural Design
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Space Requirements: Accurate space calculations
  - Function Consideration: Different functions considered
  - Density Factors: Appropriate density recommendations

- **Query**: "How do I optimize the unit mix in a residential building for market demand?"
- **Expected Output**: Unit type recommendations, market analysis, design considerations
- **Domain**: Architectural Design
- **Complexity**: High
- **Evaluation Metrics**:
  - Market Analysis: Accurate market understanding
  - Mix Optimization: Optimal unit mix recommendations
  - Design Integration: Design considerations included

### 6. Construction Technology Tests

#### Test Set 6.1: Building Information Modeling (BIM)
**Test ID: AC-CT-BIM-001 to 002**
- **Query**: "What are the benefits of BIM implementation for a mid-size construction project?"
- **Expected Output**: Specific benefits, implementation strategies, cost considerations
- **Domain**: Construction Technology
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Benefit Accuracy: Realistic BIM benefits
  - Implementation: Practical implementation strategies
  - ROI Analysis: Cost-benefit considerations

- **Query**: "How does BIM coordination prevent field conflicts during construction?"
- **Expected Output**: Coordination processes, clash detection, field benefits
- **Domain**: Construction Technology
- **Complexity**: Medium
- **Evaluation Metrics**:
  - Process Description: Accurate BIM processes
  - Clash Prevention: Effective clash detection methods
  - Field Benefits: Realistic field improvements

#### Test Set 6.2: Construction Methods
**Test ID: AC-CT-CM-001 to 001**
- **Query**: "Compare the advantages of precast vs cast-in-place concrete for mid-rise construction"
- **Expected Output**: Comparative analysis of methods, cost factors, schedule impacts
- **Domain**: Construction Technology
- **Complexity**: High
- **Evaluation Metrics**:
  - Method Comparison: Fair comparison of methods
  - Technical Factors: Technical advantages/disadvantages
  - Project Context: Context-appropriate recommendations

### 7. Code Integration with Data Sets

#### Test Set 7.1: Using Architecture Building Projects Dataset
**Test ID: AC-CID-ABP-001 to 002**
- **Query**: "Analyze the relationship between building height and construction cost per square foot using the provided dataset"
- **Expected Output**: Statistical analysis with trends and correlations
- **Domain**: Data Analysis
- **Complexity**: High
- **Required Data**: `/test_resources/datasets/architecture_building_projects.csv`
- **Evaluation Metrics**:
  - Data Analysis: Proper statistical analysis
  - Trend Identification: Accurate trend identification
  - Relationship Understanding: Clear relationship explanation

- **Query**: "Which building types have the highest and lowest energy efficiency ratings in the dataset?"
- **Expected Output**: Comparative analysis with possible explanations
- **Domain**: Data Analysis
- **Complexity**: Medium
- **Required Data**: `/test_resources/datasets/architecture_building_projects.csv`
- **Evaluation Metrics**:
  - Comparative Analysis: Accurate comparisons
  - Pattern Recognition: Identification of patterns
  - Explanatory Factors: Possible reasons for differences

#### Test Set 7.2: Using Construction Materials Properties Dataset
**Test ID: AC-CID-CMP-001 to 001**
- **Query**: "Based on the material properties dataset, which materials offer the best thermal performance for building envelopes?"
- **Expected Output**: Material comparison with thermal properties and applications
- **Domain**: Data Analysis
- **Complexity**: Medium
- **Required Data**: `/test_resources/datasets/construction_materials_properties.csv`
- **Evaluation Metrics**:
  - Material Comparison: Accurate property comparisons
  - Thermal Performance: Focus on thermal metrics
  - Application Guidance: Practical applications provided

### 8. OCR and Image Analysis Tests

#### Test Set 8.1: Architectural Drawing Analysis
**Test ID: AC-OIA-AD-001 to 002**
- **Query**: "Analyze the architectural floor plan image and describe the room layout and dimensions"
- **Expected Output**: Description of spaces, dimensions, and relationships
- **Domain**: Document Processing (OCR)
- **Complexity**: Medium
- **Required Data**: `/test_resources/images/architectural_floor_plan.png`
- **Evaluation Metrics**:
  - Spatial Recognition: Accurate space identification
  - Dimension Recognition: Correct dimension extraction
  - Layout Understanding: Proper spatial relationships

- **Query**: "Identify the construction materials and systems from the wall section detail drawing"
- **Expected Output**: List of materials, their positions, and functions
- **Domain**: Document Processing (OCR)
- **Complexity**: High
- **Required Data**: `/test_resources/images/construction_detail_drawing.png`
- **Evaluation Metrics**:
  - Material Recognition: Accurate material identification
  - System Understanding: Understanding of system functions
  - Detail Interpretation: Proper detail interpretation

## Evaluation Metrics by Domain

### Building Codes and Compliance
- **Code Accuracy**: Percentage of code references and requirements correct
- **Interpretation Quality**: How well code requirements are explained
- **Application Relevance**: Appropriateness to real-world applications

### Structural Analysis
- **Calculation Accuracy**: Mathematical accuracy of structural calculations
- **Code Application**: Proper building code application
- **Safety Factor Understanding**: Appropriate safety factor application

### Project Management
- **Schedule Accuracy**: Reasonableness of time estimates
- **Cost Estimation**: Accuracy of cost predictions
- **Risk Assessment**: Identification and mitigation of risks

### Sustainable Design
- **Environmental Knowledge**: Understanding of sustainable design principles
- **Performance Metrics**: Accuracy of performance metrics
- **Life Cycle Thinking**: Full life cycle considerations

### Design Assistance
- **Creative Problem Solving**: Innovative solutions to design challenges
- **Technical Integration**: Proper integration of technical requirements
- **Aesthetic Considerations**: Consideration of aesthetic factors

## Success Criteria
- Building Codes: >85% accuracy in code requirements
- Structural Analysis: >90% accuracy in calculations
- Project Management: >80% accuracy in estimates
- Sustainable Design: >85% accuracy in recommendations
- Design Assistance: >80% relevant solutions
- Data Analysis: >90% accuracy in dataset analysis
- OCR/Document Processing: >75% accuracy in drawing interpretation
