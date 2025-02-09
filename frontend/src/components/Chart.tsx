import React, { useState } from 'react';
import { LineChart, BarChart } from '@mui/x-charts';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Slider from '@mui/material/Slider';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';

interface ChartProps {
  data: { x: string; y: number; label: string }[];
  annualData: { label: string; totalCost: number }[];
}

const Chart: React.FC<ChartProps> = ({ data, annualData }) => {
  const [itemNb, setItemNb] = useState(annualData.length);
  const [lineItemNb, setLineItemNb] = useState(0); // Will be set after sorting
  const [skipAnimation, setSkipAnimation] = useState(false);

  const handleItemNbChange = (event: Event, newValue: number | number[]) => {
    if (typeof newValue === 'number') {
      setItemNb(newValue);
    }
  };

  const handleLineItemNbChange = (event: Event, newValue: number | number[]) => {
    if (typeof newValue === 'number') {
      setLineItemNb(newValue);
    }
  };

  // Generate a color palette
  const colors = [
    '#FF6F61',
    '#6B5B95',
    '#88B04B',
    '#F7CAC9',
    '#92A8D1',
    '#955251',
    '#B565A7',
    '#009B77',
    '#DD4124',
    '#45B8AC',
  ];

  // Group data by plan label for the line chart
  const groupedData = data.reduce<
    Record<string, { x: string; y: number }[]>
  >((acc, point) => {
    if (!acc[point.label]) acc[point.label] = [];
    acc[point.label].push({ x: point.x, y: point.y });
    return acc;
  }, {});

  // Extract January data points
  const januaryData = data.filter((point) => point.x === 'Jan');

  // Map each plan to its January cost
  const planJanuaryCosts = januaryData.map((point) => ({
    label: point.label,
    cost: point.y,
  }));

  // Sort plans from least to most expensive
  const sortedPlansByJanCost = planJanuaryCosts.sort((a, b) => a.cost - b.cost);

  // Set initial lineItemNb if not set
  React.useEffect(() => {
    if (lineItemNb === 0) {
      setLineItemNb(sortedPlansByJanCost.length);
    }
  }, [sortedPlansByJanCost.length, lineItemNb]);

  // Get labels of plans to display
  const displayedPlanLabels = sortedPlansByJanCost
    .slice(0, lineItemNb)
    .map((plan) => plan.label);

  // Filter groupedData to include only displayed plans
  const displayedGroupedData = Object.fromEntries(
    Object.entries(groupedData).filter(([label]) =>
      displayedPlanLabels.includes(label)
    )
  );

  // Prepare series data for Line Chart
  const lineSeries = Object.entries(displayedGroupedData).map(
    ([label, points], index) => ({
      data: points.map((point) => point.y),
      label,
      color: colors[index % colors.length],
    })
  );

  // Sort annualData from least to most expensive
  const sortedAnnualData = [...annualData].sort(
    (a, b) => a.totalCost - b.totalCost
  );

  // Slice the data to display only the desired number of items
  const displayedAnnualData = sortedAnnualData.slice(0, itemNb);

  // Prepare series data for Bar Chart
  const barSeries = [
    {
      data: displayedAnnualData.map((d) => d.totalCost),
      label: 'Total Annual Cost',
      color: '#2196f3',
    },
  ];

  return (
    <div>
      <Typography variant="h6" gutterBottom>
        Monthly Cost Comparison
      </Typography>
      <LineChart
        xAxis={[
          {
            scaleType: 'band',
            data: Array.from(new Set(data.map((point) => point.x))),
          },
        ]}
        series={lineSeries}
        height={400}
        width={800}
        legend={{
          position: {
            horizontal: 'right',
            vertical: 'top',
          },
        }}
        skipAnimation={skipAnimation}
      />

      <Box sx={{ width: '80%', margin: 'auto', mt: 4 }}>
        <Typography id="line-item-number" gutterBottom>
          Number of Plans to Display in Line Chart
        </Typography>
        <Slider
          value={lineItemNb}
          onChange={handleLineItemNbChange}
          valueLabelDisplay="auto"
          step={1}
          marks
          min={1}
          max={sortedPlansByJanCost.length}
          aria-labelledby="line-item-number"
        />
      </Box>

      <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
        Annual Cost Comparison
      </Typography>
      <BarChart
        xAxis={[{ scaleType: 'band', data: displayedAnnualData.map((d) => d.label) }]}
        series={barSeries}
        height={400}
        width={800}
        skipAnimation={skipAnimation}
        legend={{
          position: {
            horizontal: 'right',
            vertical: 'top',
          },
        }}
      />

      <Box sx={{ width: '80%', margin: 'auto', mt: 4 }}>
        <Typography id="bar-item-number" gutterBottom>
          Number of Plans to Display in Bar Chart
        </Typography>
        <Slider
          value={itemNb}
          onChange={handleItemNbChange}
          valueLabelDisplay="auto"
          step={1}
          marks
          min={1}
          max={annualData.length}
          aria-labelledby="bar-item-number"
        />
      </Box>

      <Box sx={{ width: '80%', margin: 'auto', mt: 4 }}>
        <FormControlLabel
          control={
            <Checkbox
              checked={skipAnimation}
              onChange={(event) => setSkipAnimation(event.target.checked)}
            />
          }
          label="Skip Animation"
          sx={{ mb: 2 }}
        />
      </Box>
    </div>
  );
};

export default Chart;




// import React from 'react';
// import { LineChart } from '@mui/x-charts';

// interface ChartProps {
//   data: { x: string; y: number; label: string }[];
// }

// const Chart: React.FC<ChartProps> = ({ data }) => {
//   // Group data by plan label
//   const groupedData = data.reduce<Record<string, { x: string; y: number }[]>>((acc, point) => {
//     if (!acc[point.label]) acc[point.label] = [];
//     acc[point.label].push({ x: point.x, y: point.y });
//     return acc;
//   }, {});

//   return (
//     <LineChart
//       xAxis={[
//         {
//           scaleType: 'band',
//           data: Array.from(new Set(data.map((point) => point.x))), // Unique month labels
//         },
//       ]}
//       series={Object.entries(groupedData).map(([label, points]) => ({
//         data: points.map((point) => point.y), // Use Y values (monthly costs)
//         label, // Plan name as label
//         color: `#${Math.floor(Math.random() * 16777215).toString(16)}`, // Random color
//       }))}
//       height={400}
//       width={800}
//     />
//   );
// };

// export default Chart;

