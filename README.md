# Health Insurance Comparison Tool

## Overview
The Health Insurance Comparison Tool is a web application that allows users to compare various health insurance plans based on projected costs. Users can input their expected medical expenses and personal financial details, and the tool will calculate estimated costs for each plan, including monthly and annual breakdowns, tax savings, and out-of-pocket expenses.

![Alt Text](https://github.com/Pixel-Pilot28/Health-Insurance-Comparison-Tool/blob/main/HealthComparisonApp_V1.gif)

The application features:
- A **React-based frontend** for user input and visualization.
- A **FastAPI backend** for processing cost calculations.
- **Data storage and retrieval** to maintain user inputs across sessions.
- **Dynamic charts** displaying cost comparisons for better decision-making.

## Features
- **User Data Input:** Users enter their expected medical needs, tax details, and financial information.
- **Real-Time Cost Calculation:** The backend processes costs using plan details and personal inputs.
- **Graphical Comparisons:** Monthly and yearly cost visualizations help users compare plans easily.
- **HSA & FSA Integration:** The tool calculates tax savings and HSA/FSA usage.
- **Plan Filtering & Sorting:** Users can focus on specific plans based on affordability and benefits.

## Getting Started

### Prerequisites
Ensure you have the following installed:
- [Node.js](https://nodejs.org/) (for frontend development)
- [Python 3.9+](https://www.python.org/) (for the backend)
- [FastAPI](https://fastapi.tiangolo.com/) and required Python dependencies

### Installation & Setup

#### 1. Clone the Repository
```sh
 git clone https://github.com/Pixel-Pilot28/Health-Insurance-Comparison-Tool.git
 cd health-insurance-tool
```

#### 2. Set Up the Backend
```sh
 cd backend
 python -m venv venv
 source venv/bin/activate  # On Windows use: venv\Scripts\activate
 pip install -r requirements.txt
```

#### 3. Run the Backend API
```sh
 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
This starts the FastAPI server at `http://127.0.0.1:8000/api`.

#### 4. Set Up the Frontend
```sh
 cd ../frontend
 npm install
```

#### 5. Run the Frontend
```sh
 npm start
```
This starts the frontend on `http://localhost:3000/`.

## How the App Works
1. **Data Input:** Users enter financial details (income, tax rate, HSA/FSA contributions) and expected medical service usage.
2. **Backend Processing:** The FastAPI server calculates projected costs using a predefined dataset of insurance plans.
3. **Comparison Charts:** The frontend fetches calculated results and displays them as a monthly cost line chart and an annual cost bar chart.
4. **Plan Evaluation:** Users analyze costs to select the most cost-effective plan for their needs.

## API Endpoints
The backend provides:
- **`POST /api/calculate`** – Accepts user inputs and returns calculated plan costs.
- **`GET /api/health-plans`** – Fetches available insurance plans.

## Known Limitations
While this tool provides a helpful estimate, it has some limitations:
1. **Simplified Data Representation:**
   - Some plan details (e.g., "15% $450 Calendar Year Deductible") have been converted into simplified numerical values.
   - If multiple numbers existed for a given service (e.g., 15% or 30%), we picked the lower value. Oftentimes, the plan brochures will detail how instances like this should be handled but it would be too difficult to hard code these attributes in every case. 
2. **Approximate Costs:**
   - This tool estimates costs based on expected service use but cannot guarantee exact real-world expenses given local variance.
3. **Plan-Specific Rules:**
   - Certain nuances in insurance policies (e.g., tiered copayments, exceptions) may not be fully captured.
4. **Tax & HSA/FSA Assumptions:**
   - The tool assumes a flat effective tax rate and does not consider state tax variations or complicated tax situations.

## Future Improvements
- **More detailed cost breakdowns, including service-specific pricing insights.**
- **A recommendation engine that will take your attitudes like risk tolerance and cost loading into account in helping you pick a health plan.**
- **File upload to allow users to upload their own insurance/cost datasets.**
- **Support for complex deductible structures.**
- **Enhanced data parsing to handle more text-based policy descriptions.**
- **User authentication and saved preferences.**

## Contributing
Please submit pull requests or open issues for feature requests and bug reports. If you would like to work on this project, feel free to reach out!

## License
This project is licensed under the MIT License.

