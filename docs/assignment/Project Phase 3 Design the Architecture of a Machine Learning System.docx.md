**Student Name:**	**Weight:**	20%

**Student ID:**	**Marks:**	/70

# **Design the Architecture of a Machine Learning System**

## **Introduction**

In machine learning projects, system design involves structuring and planning all the components needed to develop, deploy, and maintain a machine learning system. This includes defining the architecture, selecting the technology stack, designing data pipelines, organizing model training and evaluation, and setting up deployment and monitoring strategies. Effective system design helps ensure the solution is scalable, reliable, maintainable, and efficient.

The main objective of the system design phase is to create a comprehensive blueprint for the machine learning system. This blueprint outlines the architecture, data pipeline, model training process, and deployment strategy. This guides the implementation phase.

## **Instructions**

The system design provides a detailed and structured plan for the machine learning project, from data collection to deployment. By thoroughly documenting all aspects and considerations of your project, the system design helps ensure that your work can be implemented easily.

1. Review the marking criteria provided below.

2. Part A – High-level Architecture

   1. Data source: Identify all the sources of data (e.g., CSV files, databases, APIs).

   2. Data storage: Choose a suitable storage system for raw and processed data (e.g., SQL/NoSQL database).

   3. Data processing: Outline the ETL (Extract, Transform, Load) processes.

   4. Model training: Define the environment and framework for training the machine learning model (e.g., Tensorflow, PyTorch).

   5. Model evaluation: Establish criteria and methods for evaluating model performance (e.g., RMSE, MAE, Accuracy, F1-Score, Recall, Precision, ROC curve).

   6. Deployment: Specify the deployment environment and tools (e.g., cloud services).

   7. Monitoring and maintenance: Plan for ongoing monitoring and maintenance.

3. Part B – Detailed Architecture diagram

Use a software application of your choice to create a detailed architecture diagram that represents the system design of a machine learning project. Here are some suggestions for software:

* [https://app.diagrams.net/](https://app.diagrams.net/)

* [Microsoft Visio](https://www.microsoft.com/en-ca/microsoft-365/visio/flowchart-software)

* [Draw.io](https://app.diagrams.net/) 

  1. Data flow: Show the flow of data from source to storage, processing, model training, evaluation and deployment.

  2. Interconnection: Illustrate how different components interact with each other.

  3. Technologies: Annotate the diagram with specific technologies or the tools used at each stage.

4. Part C – Outline the Data Pipeline

   1. Data Collection

      1. Sources: List and describe the data sources (e.g., patient diagnostic measures, customer interaction logs, transaction records).

      2. Methods: Explain how the data will be collected from these sources (e.g., API calls, web scraping).

      3. Frequency: Specify the frequency of data collection (e.g., real-time, daily batch)

   2. Data Processing

      1. Cleaning: Describe the steps for data cleaning (e.g., handle missing values, removing duplicates).

      2. Transformation: Outline data transformation processes (e.g., normalization, encoding categorical variables).

      3. Feature engineering: Detail the creation of new features from raw data (e.g., aggregations, calculations).

   3. Data Storage

      1. Raw data storage: Define where and how raw data will be stored (e.g., data frame, csv file).

      2. Processed data storage: Specify the storage for cleaned data (e.g., data frame, csv file).

5. Part D: Model Training

   1. Model selection

      1. Algorithm selection: Justify the choice of machine learning algorithms (e.g., Random Forest, CNN, RNN)

      2. Frameworks: Specify the frameworks and libraries used for model training (e.g., scikit-learn, Pycaret, Keras, TensorFlow)

   2. Training Process

      1. Data splitting: Describe how the data will be split into training, validation, and test set.

      2. Hyperparameter tuning: Outline the process of hyperparameter tuning (e.g., Grid search, random search).

      3. Training environment: Specify the hardware and software environment for training (e.g.,  cloud instance, local GPU).

   3. Model Evaluation

      1. Metrics: Define evaluation metrics (e.g., RMSE, MAE, Accuracy, F1-Score, Recall, Precision, ROC curve).

      2. Validation Strategy: Describe the validation strategy (e.g., cross-validation).

      3. Benchmarking: Set benchmarks for model performance.

6. Part E: Deployment strategy

   1. Infrastructure: Choose the deployment infrastructure (e.g., cloud platforms like AWS, Azure, Google Cloud).

7. Part F: Develop a Progress Report 

   1. Review the *Progress Report Template* in Brightspace. 

   2. Use this template in each phase of the project to divide and track project work.

8. Only one copy needs to be submitted per team. Your submission should include:

   1. Detailed answers to the questions in steps 2, 4 and 5 (.docx or .pdf)

   2. Detailed architecture diagram (.pdf)

   3. A completed progress report (.docx or .pdf)

   4. The names of all team members listed at the beginning of each document 

## **Marking Criteria**

| Criteria | Needs Improvement | Good | Excellent | Marks |
| ----- | ----- | ----- | ----- | :---: |
| **Part A: High Level Architecture** | High-Level architecture is missing. (0 marks) | Some of the components are missing, or components of high-level architecture are missing information. (5 marks) | All the mentioned high-level architecture components are properly covered and relevant to the project. (10 marks)  | **/10** |
| **Part B: Detailed Architecture Diagram** | A detailed architecture diagram is missing.  (0 marks) | A diagram is submitted but lacks details. All the mentioned components are not annotated. (10 marks) | A clear, detailed, and annotated architecture diagram is included. (20 marks) | **/20** |
| **Part C: Data Pipeline** | One or two components of the data pipeline are missing. (3 marks)  | All three components (data collection, data processing and data storage) are outlined but ineffective. (7 marks) | All three components are very clear, relevant and insightful. (10 marks)  | **/10** |
| **Part D: Model Training** | The model training part is missing or mostly incomplete. (2 marks) | A model training part has been added, but some areas are incomplete. (6 marks) | All the model training components are complete, clear and concise. (10 marks) | **/10** |
| **Part E:  Deployment Strategy** | The deployment strategy is missing. (0 marks) | The deployment strategy is added but incomplete. (6 marks) | The deployment strategy is  complete,clear and concise. (10 marks) | **/10** |
| **Part F: Progress Report** | The progress report is missing or incomplete  (2 marks) | The progress reports lack detail, and/or tasks are not evenly distributed. (6 marks) | The progress report is complete, and work has been evenly distributed. (10 marks) | **/10** |
| **Total** |  |  |  | **/70** |

