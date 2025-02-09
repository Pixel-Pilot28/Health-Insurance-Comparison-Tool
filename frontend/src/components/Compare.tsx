import React, { useEffect, useState } from 'react';
import { Typography, Checkbox, FormControlLabel, Stack } from '@mui/material';
import Chart from './Chart'; // Import the Chart component
import { calculateCost, getUserData } from '../api/apiClient'; 


const Compare: React.FC = () => {
  const [healthPlans, setHealthPlans] = useState<Record<string, any>>({});
  const [selectedSeries, setSelectedSeries] = useState<string[]>([]);


useEffect(() => {
  const fetchData = async () => {
    try {
      const userData = await getUserData();
      console.log("Compare.tsx - Retrieved user data:", userData);

      if (userData) {
        const response = await calculateCost(userData);
        console.log("Compare.tsx - API response before setHealthPlans:", response.plans);
        
        if (response && response.plans) {
          setHealthPlans(response.plans);
          setSelectedSeries(Object.keys(response.plans));
        }
      }
    } catch (error: any) {
      console.error("Error fetching data in Compare:", error.message);
    }
  };

  fetchData();
}, []);

// Transform data for the graph
const seriesData = Object.entries(healthPlans).map(([planId, planData]) => {
  const monthlyBreakdown = planData.monthly_breakdown || {};
  const dataPoints = Object.entries(monthlyBreakdown).map(([month, cost]) => ({
    x: month,
    y: parseFloat(cost as string), // Ensure costs are numeric
  }));
  return { data: dataPoints, label: planData.plan_name, color: `#${Math.floor(Math.random() * 16777215).toString(16)}` };
});

  const toggleSeries = (planId: string) => {
    setSelectedSeries((prev) =>
      prev.includes(planId) ? prev.filter((id) => id !== planId) : [...prev, planId]
    );
  };

  const graphData = Object.entries(healthPlans)
  .filter(([planId]) => selectedSeries.includes(planId))
  .flatMap(([planId, planData]) =>
    Object.entries(planData.monthly_breakdown).map(([month, cost]) => ({
      x: month, // Month name
      y: cost as number, // Monthly cost
      label: planData.plan_name, // Plan name
    }))
  );

  const lineChartData = Object.entries(healthPlans).flatMap(([planId, planData]) =>
    Object.entries(planData.monthly_breakdown).map(([month, cost]) => ({
      x: month,
      y: Number(cost), // Ensure numeric values
      label: planData.plan_name as string, // Ensure label is string
    }))
  );
  
  const annualData = Object.entries(healthPlans).map(([planId, planData]) => ({
    label: planData.plan_name as string,
    totalCost: Number(planData.annual_cost),
  }));
  
  return (
    <div>
      <Typography variant="h5" gutterBottom>
        Compare Health Plans
      </Typography>
      <Chart data={lineChartData} annualData={annualData} />
    </div>
  );
};

export default Compare;
