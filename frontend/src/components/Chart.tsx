import React, { useState, useEffect } from 'react';
import { LineChart, BarChart } from '@mui/x-charts';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Slider from '@mui/material/Slider';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import Grid from '@mui/material/Grid';

interface ChartProps {
  data: { x: string; y: number; label: string }[];
  annualData: { label: string; totalCost: number }[];
}

const Chart: React.FC<ChartProps> = ({ data, annualData }) => {
  const [itemNb, setItemNb] = useState(0);
  const [lineItemNb, setLineItemNb] = useState(0);
  const [skipAnimation, setSkipAnimation] = useState(false);
  const [planColors, setPlanColors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (annualData.length > 0) {
      setItemNb(annualData.length);
      setLineItemNb(annualData.length);

      // Define a consistent color palette
      const colors = [
        '#FF6F61', '#6B5B95', '#88B04B', '#F7CAC9', '#92A8D1', '#955251',
        '#B565A7', '#009B77', '#DD4124', '#45B8AC', '#EFC050', '#5B5EA6'
      ];

      // Assign colors to plans in sorted order
      const sortedAnnualData = [...annualData].sort((a, b) => a.totalCost - b.totalCost);
      const colorMapping: Record<string, string> = {};
      sortedAnnualData.forEach((plan, index) => {
        colorMapping[plan.label] = colors[index % colors.length];
      });

      setPlanColors(colorMapping);
    }
  }, [annualData]);

  if (data.length === 0 || annualData.length === 0) {
    return <Typography variant="h6">No data to display</Typography>;
  }

  const handleLineItemNbChange = (event: Event, newValue: number | number[]) => {
    if (typeof newValue === 'number') {
      setLineItemNb(newValue);
    }
  };

  const handleItemNbChange = (event: Event, newValue: number | number[]) => {
    if (typeof newValue === 'number') {
      setItemNb(newValue);
    }
  };

  // Sort annualData from least to most expensive
  const sortedAnnualData = [...annualData].sort((a, b) => a.totalCost - b.totalCost);
  const displayedAnnualData = sortedAnnualData.slice(0, itemNb);

  // Prepare data for bar chart
  const barSeries = [
    {
      data: displayedAnnualData.map((d) => d.totalCost),
      label: 'Total Annual Cost',
      color: '#2196f3',
    },
  ];

  // Group data by plan label for the line chart
  const groupedData = data.reduce<Record<string, { x: string; y: number }[]>>((acc, point) => {
    if (!acc[point.label]) acc[point.label] = [];
    acc[point.label].push({ x: point.x, y: point.y });
    return acc;
  }, {});

  // Sort plans for the line chart using the same order as the bar chart
  const sortedPlans = sortedAnnualData.map((plan) => plan.label);
  const displayedPlans = sortedPlans.slice(0, lineItemNb);

  // Prepare data for line chart
  const lineSeries = displayedPlans.map((label) => ({
    data: groupedData[label]?.map((point) => point.y) || [],
    label,
    color: planColors[label] || '#000000', // Use assigned color or fallback to black
  }));

  return (
    <Box sx={{ width: '90%', margin: 'auto' }}>
      <Typography variant="h6" gutterBottom>
        Monthly Cost Comparison
      </Typography>

      <Grid container spacing={2} alignItems="center">
        <Grid item xs={9}>
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
            skipAnimation={skipAnimation}
            slotProps={{ legend: { hidden: true } }} // Correctly hides old legend
          />
        </Grid>

        {/* Custom Legend */}
        <Grid item xs={3}>
          <Box sx={{ overflowY: 'auto', maxHeight: 400 }}>
            <Typography variant="subtitle1" gutterBottom>
              Plan Legend
            </Typography>
            {displayedPlans.map((label) => (
              <Box key={label} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Box
                  sx={{
                    width: 16,
                    height: 16,
                    backgroundColor: planColors[label],
                    marginRight: 1,
                  }}
                />
                <Typography variant="body2">{label}</Typography>
              </Box>
            ))}
          </Box>
        </Grid>
      </Grid>

      {/* Sliders Section */}
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', mt: 4 }}>
        <Typography id="line-item-number" gutterBottom>
          Number of Plans to Display in Line Chart
        </Typography>
        <Slider
          sx={{ width: '80%' }}
          value={lineItemNb}
          onChange={handleLineItemNbChange}
          valueLabelDisplay="auto"
          step={1}
          marks
          min={1}
          max={annualData.length}
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
      />

      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', mt: 4 }}>
        <Typography id="bar-item-number" gutterBottom>
          Number of Plans to Display in Bar Chart
        </Typography>
        <Slider
          sx={{ width: '80%' }}
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

      {/* Animation Toggle */}
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', mt: 4 }}>
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
    </Box>
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

