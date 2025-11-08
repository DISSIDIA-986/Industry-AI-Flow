# Architecture and Construction RAG Performance Test

## Executive Summary
This test evaluates the RAG system's specific capabilities when handling architecture and construction domain queries, including code compliance, structural analysis, project management, and design assistance.

## Test Setup

### Test Environment
- **Dataset Sources**: 
  - `/test_resources/datasets/architecture_building_projects.csv`
  - `/test_resources/datasets/construction_materials_properties.csv`
  - `/test_resources/datasets/architecture_construction_test_dataset.json`

- **Image Data Sources**:
  - `/test_resources/images/architectural_floor_plan.png`
  - `/test_resources/images/construction_detail_drawing.png`

### Test Categories and Metrics

## Category 1: Code Compliance Accuracy

### Test 1.1: International Building Code Queries
**Test Query**: "According to IBC 2021, what are the minimum ceiling heights for residential units?"

**Expected Response**: 
- Section 1208.1: Minimum habitable room ceiling height of 7 feet 6 inches
- Exceptions for sloped ceilings and beams
- Reference to specific building code section

**Evaluation Metrics**:
- Code Accuracy: Percentage of correct references
- Detail Level: Adequacy of requirements explanation
- Safety Factors: Proper inclusion of safety margins

### Test 1.2: ADA Compliance Queries
**Test Query**: "How should I design an accessible route in a multi-level building?"

**Expected Response**:
- Ramp specifications (slope, width, landings)
- Elevator requirements
- Doorway clearances
- Visual and tactile elements

**Evaluation Metrics**:
- Requirement Coverage: All ADA requirements included
- Practical Application: Feasible design solutions
- Safety Compliance: Proper safety margins

## Category 2: Structural Analysis Performance

### Test 2.1: Load Calculation Accuracy
**Test Query**: "Calculate the total dead load for a 10m x 12m concrete slab with 250mm thickness"

**Expected Response**:
- Slab volume: 10 * 12 * 0.25 = 30 m³
- Concrete density: ~2400 kg/m³
- Weight: 30 * 2400 * 9.81 = 706,320 N
- Dead load per unit area: 706,320 / (10 * 12) = 5.89 kN/m²

**Required Data**: `/test_resources/datasets/construction_materials_properties.csv`
**Evaluation Metrics**:
- Calculation Accuracy: Mathematical correctness
- Methodology: Proper calculation approach
- Safety Factors: Appropriate factors of safety

### Test 2.2: Material Performance Comparison
**Test Query**: "Compare the compressive strength of steel and concrete for the same cross-sectional area"

**Expected Response**:
- Steel: 250-450 MPa yield strength
- Concrete: 20-40 MPa compressive strength
- Application differences: Tension vs compression

**Required Data**: `/test_resources/datasets/construction_materials_properties.csv`
**Evaluation Metrics**:
- Material Properties: Accuracy of property values
- Comparative Analysis: Fair comparison methodology
- Application Context: Appropriate usage contexts

## Category 3: Project Management Intelligence

### Test 3.1: Duration Estimation
**Test Query**: "What is the typical duration for a 15-story commercial building?"

**Expected Response**:
- Foundation: 2-3 months
- Superstructure: 12-15 months
- MEP and fit-out: 8-10 months
- Total: 22-28 months depending on complexity

**Required Data**: `/test_resources/datasets/architecture_building_projects.csv`
**Evaluation Metrics**:
- Estimation Accuracy: Reasonable time ranges
- Phase Breakdown: Proper phase durations
- Complexity Factors: Consideration of project factors

### Test 3.2: Cost Analysis
**Test Query**: "Analyze construction costs by building height using project data"

**Expected Response**:
- Cost per square foot trends by height
- Structural system impacts
- Foundation and lateral system costs
- Elevator and mechanical systems

**Required Data**: `/test_resources/datasets/architecture_building_projects.csv`
**Evaluation Metrics**:
- Data Analysis: Proper statistical analysis
- Trend Identification: Accurate trend detection
- Cost Relationships: Correct cost-height relationships

## Category 4: Sustainable Design Knowledge

### Test 4.1: Energy Efficiency
**Test Query**: "What building features contribute most to LEED energy performance points?"

**Expected Response**:
- Energy modeling and optimization
- High-efficiency HVAC systems
- Building envelope performance
- Renewable energy integration

**Evaluation Metrics**:
- LEED Knowledge: Accurate credit information
- Technical Accuracy: Proper technical information
- Implementation Feasibility: Practical implementation methods

### Test 4.2: Material Sustainability
**Test Query**: "Evaluate the environmental impact of different structural systems"

**Expected Response**:
- Steel: High energy production, recyclable
- Concrete: Lower energy production, durable
- Timber: Renewable, carbon sequestration
- Life cycle assessment factors

**Evaluation Metrics**:
- Environmental Knowledge: Accurate impact information
- Lifecycle Thinking: Full lifecycle considerations
- Balance Understanding: Performance vs environmental balance

## Category 5: Design Assistance Capabilities

### Test 5.1: Space Planning
**Test Query**: "Design the layout for a 2000 sq ft open office space"

**Expected Response**:
- Workstation arrangements
- Collaboration areas
- Circulation patterns
- Natural light optimization

**Evaluation Metrics**:
- Functionality: Practical space arrangement
- Regulations: Compliance with building codes
- Efficiency: Optimal space utilization
- User Experience: Good user experience

### Test 5.2: System Integration
**Test Query**: "How do I integrate MEP systems in a high-performance building?"

**Expected Response**:
- Coordination requirements
- Energy efficiency strategies
- Maintenance access
- System redundancy

**Evaluation Metrics**:
- Technical Accuracy: Accurate technical information
- Coordination: Proper system coordination
- Performance: High-performance design approaches

## Category 6: Document Processing and OCR Performance

### Test 6.1: Drawing Interpretation
**Test Query**: "Analyze the architectural floor plan image and describe the unit layout"

**Required Data**: `/test_resources/images/architectural_floor_plan.png`
**Expected Response**:
- Room identifications and functions
- Spatial relationships
- Dimensions and scales
- Key architectural features

**Evaluation Metrics**:
- Recognition Accuracy: Correct element identification
- Spatial Understanding: Proper relationship analysis
- Detail Level: Adequate level of detail
- Accuracy: Factual accuracy of description

### Test 6.2: Detail Drawing Analysis
**Test Query**: "Interpret the construction detail drawing and explain the wall assembly"

**Required Data**: `/test_resources/images/construction_detail_drawing.png`
**Expected Response**:
- Material sequence and properties
- Construction method
- Performance characteristics
- Installation considerations

**Evaluation Metrics**:
- Material Recognition: Accurate material identification
- Assembly Understanding: Proper understanding of assembly
- Technical Accuracy: Correct technical information
- Application: Practical application knowledge

## Integration Performance Tests

### Test 7.1: Multi-Source Query Processing
**Test Query**: "Based on historical projects and material properties, recommend the best structural system for a 10-story office building"

**Required Data**: 
- `/test_resources/datasets/architecture_building_projects.csv`
- `/test_resources/datasets/construction_materials_properties.csv`
**Expected Response**:
- Historical precedent analysis
- Material performance comparison
- Recommendation with rationale
- Cost and schedule implications

**Evaluation Metrics**:
- Data Integration: Proper integration of multiple datasets
- Analysis Quality: Comprehensive analysis
- Recommendation Quality: Well-reasoned recommendation
- Supporting Evidence: Appropriate supporting evidence

## Performance Benchmarks

### Speed Metrics
- **Query Response Time**: <4 seconds for simple queries
- **Analysis Response Time**: <10 seconds for complex analysis
- **Document Processing Time**: <8 seconds for basic OCR tasks

### Accuracy Metrics
- **Code Compliance**: >90% accuracy for building codes
- **Calculations**: >95% accuracy for structural calculations
- **Cost Estimation**: >85% accuracy for cost estimates
- **Material Properties**: >95% accuracy for material data
- **Drawing Analysis**: >80% accuracy for image interpretation

### Quality Metrics
- **Completeness**: All relevant aspects covered
- **Clarity**: Clear and understandable responses
- **Relevance**: Responses directly address query
- **Actionability**: Practical and actionable recommendations
- **Technical Accuracy**: Technically correct information
- **Safety Compliance**: Proper safety considerations

## Success Criteria

### Minimum Pass Rates
- Code Compliance Tests: 85% minimum
- Structural Analysis Tests: 90% minimum
- Project Management Tests: 80% minimum
- Sustainable Design Tests: 85% minimum
- Design Assistance Tests: 80% minimum
- Document Processing Tests: 75% minimum
- Integration Tests: 85% minimum

### Overall System Evaluation
- **Architecture Domain Proficiency**: >85% average across all categories
- **Construction Domain Proficiency**: >80% average across all categories
- **User Satisfaction**: >85% satisfaction with responses
- **Technical Accuracy**: >90% technically correct responses