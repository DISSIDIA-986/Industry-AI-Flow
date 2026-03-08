# Progress Report -- Phase 4

**Project:** Industry AI Flow -- AI-Powered Construction Industry Platform

**Program:** Integrated Artificial Intelligence, SAIT Capstone Project

**Team Members:**
- Angel Daniel Bustamante Perez
- Jason Niu
- Jack Si

**Instructor:** Reeta

**Date:** March 2026

---

## Project Status Summary

Phase 4 focuses on the machine learning development process using the CRISP-DM methodology. We built, trained, and evaluated multiple regression models on our 10,000-record construction cost dataset. The system is feature-complete and we are preparing for the Capstone Showcase.

---

## Task Distribution

### Jason Niu -- Software Development Lead

| Task | Status | Description |
|------|--------|-------------|
| Jupyter notebook development | Complete | Full CRISP-DM notebook with EDA, data prep, model building, and evaluation |
| Data preprocessing pipeline | Complete | Feature engineering, standardization, one-hot encoding, train/test split |
| Model training (6 algorithms) | Complete | Ridge, Lasso, ElasticNet, Random Forest, Gradient Boosting, SVR |
| Hyperparameter tuning | Complete | GridSearchCV on Gradient Boosting and Ridge Regression |
| Model evaluation & visualization | Complete | Performance comparison charts, residual analysis, feature importance |
| Production model integration | Complete | Ridge Regression deployed as FastAPI endpoint with confidence intervals |
| System testing & optimization | Complete | 516+ unit tests, performance optimization, security hardening |

### Jack Si -- Construction Domain Expert

| Task | Status | Description |
|------|--------|-------------|
| Dataset curation | Complete | Provided 10,000-row construction project dataset with 25 features |
| Feature identification | Complete | Identified key cost drivers from construction industry knowledge |
| Business understanding documentation | Complete | Defined problem context, objectives, and business impact |
| Model output validation | Complete | Verified prediction results against industry experience |
| Demo scenario preparation | In Progress | Preparing realistic construction project scenarios for showcase |

### Angel Daniel Bustamante Perez -- Project Support

| Task | Status | Description |
|------|--------|-------------|
| Project coordination | Complete | Team communication and milestone tracking |
| Document preparation | In Progress | Assignment submissions and presentation materials |
| Testing support | Complete | Assisted with system testing and bug reporting |
| Presentation preparation | In Progress | Preparing Capstone Showcase presentation slides |

---

## Milestones

| Milestone | Target Date | Status |
|-----------|-------------|--------|
| Phase 1: Project proposal | Completed | Done |
| Phase 2: Data collection & preprocessing | Completed | Done |
| Phase 3: System architecture design | Completed | Done |
| Phase 4: Model development (CRISP-DM) | March 2026 | Done |
| Full system integration | Completed | Done |
| 36 rounds of test-driven improvement | Completed | Done |
| Demo preparation & rehearsal | Late March 2026 | In Progress |
| Capstone Showcase | Late March / Early April 2026 | Upcoming |

---

## Challenges and Solutions

| Challenge | Solution |
|-----------|----------|
| Selecting the right ML algorithm | We trained and compared 6 different algorithms to find the best fit |
| Avoiding data leakage | We excluded post-hoc outcome columns (actual_cost, actual_duration) from features |
| Balancing model accuracy vs. interpretability | We chose Ridge Regression for production (interpretable) while noting Gradient Boosting achieves higher R2 |
| Feature engineering for categorical variables | Applied one-hot encoding for project_type (12 categories) and location (15 cities) |
| Ensuring model generalization | Used 5-fold cross-validation and verified train/test metrics are consistent (no overfitting) |

---

## Next Steps

1. Final demo rehearsal with realistic construction project scenarios
2. Prepare Capstone Showcase presentation slides
3. Ensure system stability during live demo
4. Complete final assignment submissions
