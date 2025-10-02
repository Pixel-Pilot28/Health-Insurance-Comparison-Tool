import React, { useEffect, useState } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  ButtonGroup,
  Paper,
  Avatar,
  Stack,
  Divider,
  LinearProgress,
  Tooltip,
  IconButton,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Skeleton
} from '@mui/material';
import {
  TrendingUp,
  AttachMoney,
  LocalHospital,
  Savings,
  CompareArrows,
  Visibility,
  VisibilityOff,
  Star,
  Psychology
} from '@mui/icons-material';
import { LineChart, BarChart } from '@mui/x-charts';
import { calculateCost, getUserData } from '../api/apiClient';
import { useNavigation } from '../contexts/NavigationContext';

interface PlanData {
  plan_name: string;
  annual_cost: number;
  monthly_breakdown: Record<string, number>;
  tax_savings: number;
  cumulative_cost: number;
  hsa_growth: number;
  unused_hsa?: number;
  unused_fsa?: number;
}

const Compare: React.FC = () => {
  const { navigateToTab } = useNavigation();
  const [healthPlans, setHealthPlans] = useState<Record<string, PlanData>>({});
  const [selectedPlans, setSelectedPlans] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<'chart' | 'cards'>('cards');
  const [showTaxBenefits, setShowTaxBenefits] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const savedData = await getUserData();

        if (savedData) {
          console.log('Compare: Retrieved saved data:', savedData);
          // The backend expects the full payload structure with userData and inputDetails
          const response = await calculateCost(savedData);
          console.log('Compare: Calculate response:', response);
          
          if (response && response.plans) {
            setHealthPlans(response.plans);
            // Auto-select top 3 most affordable plans
            const sortedPlans = Object.entries(response.plans)
              .sort(([, a], [, b]) => (a as PlanData).annual_cost - (b as PlanData).annual_cost)
              .slice(0, 3)
              .map(([id]) => id);
            setSelectedPlans(sortedPlans);
          }
        } else {
          setError('No user data found. Please fill out the data input form first.');
        }
      } catch (error: any) {
        setError(error.message || 'Failed to load health plan data');
        console.error("Error fetching data in Compare:", error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const togglePlanSelection = (planId: string) => {
    setSelectedPlans(prev =>
      prev.includes(planId)
        ? prev.filter(id => id !== planId)
        : [...prev, planId]
    );
  };

  const getDisplayedPlans = () => {
    return Object.entries(healthPlans)
      .sort(([, a], [, b]) => (a as PlanData).annual_cost - (b as PlanData).annual_cost);
  };

  const getBestValue = () => {
    const plans = getDisplayedPlans();
    return plans.length > 0 ? plans[0][0] : null;
  };

  const getHighestSavings = () => {
    const plans = Object.entries(healthPlans);
    return plans.reduce((best, [id, plan]) => {
      const planData = plan as PlanData;
      const totalSavings = planData.tax_savings + (planData.hsa_growth || 0);
      const bestSavings = best ? healthPlans[best].tax_savings + (healthPlans[best].hsa_growth || 0) : 0;
      return totalSavings > bestSavings ? id : best;
    }, null as string | null);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const PlanCard = ({ planId, planData, isSelected, isBestValue, hasHighestSavings }: {
    planId: string;
    planData: PlanData;
    isSelected: boolean;
    isBestValue: boolean;
    hasHighestSavings: boolean;
  }) => {
    const totalSavings = planData.tax_savings + (planData.hsa_growth || 0);
    const effectiveCost = planData.annual_cost;
    const costWithoutBenefits = effectiveCost + totalSavings;

    return (
      <Card
        sx={{
          position: 'relative',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          border: isSelected ? '3px solid #1976d2' : '1px solid #e0e0e0',
          boxShadow: isSelected ? '0 8px 25px rgba(25, 118, 210, 0.3)' : '0 2px 8px rgba(0,0,0,0.1)',
          transform: isSelected ? 'scale(1.02)' : 'scale(1)',
          '&:hover': {
            transform: 'scale(1.02)',
            boxShadow: '0 8px 25px rgba(0,0,0,0.15)',
          },
        }}
        onClick={() => togglePlanSelection(planId)}
      >
        {/* Badge Indicators */}
        {isBestValue && (
          <Chip
            label="Best Value"
            color="success"
            size="small"
            icon={<Star />}
            sx={{ position: 'absolute', top: 8, left: 8, zIndex: 1 }}
          />
        )}
        {hasHighestSavings && (
          <Chip
            label="Highest Savings"
            color="warning"
            size="small"
            icon={<Savings />}
            sx={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}
          />
        )}

        <CardContent sx={{ pt: isBestValue || hasHighestSavings ? 5 : 3 }}>
          <Box display="flex" alignItems="center" mb={2}>
            <Avatar sx={{ bgcolor: isSelected ? '#1976d2' : '#f5f5f5', mr: 2 }}>
              <LocalHospital color={isSelected ? 'inherit' : 'action'} />
            </Avatar>
            <Box>
              <Typography variant="h6" component="h3" fontWeight="600">
                {planData.plan_name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Plan ID: {planId}
              </Typography>
            </Box>
            <Box ml="auto">
              <IconButton>
                {isSelected ? <Visibility color="primary" /> : <VisibilityOff />}
              </IconButton>
            </Box>
          </Box>

          <Divider sx={{ my: 2 }} />

          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="h4" color="primary" fontWeight="700">
                  {formatCurrency(effectiveCost)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Annual Cost
                </Typography>
              </Box>
            </Grid>

            {showTaxBenefits && totalSavings > 0 && (
              <Grid item xs={12}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    bgcolor: '#f8f9fa',
                    borderRadius: 2,
                  }}
                >
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="body2" color="text.secondary">
                      Cost before tax benefits
                    </Typography>
                    <Typography variant="body2" sx={{ textDecoration: 'line-through' }}>
                      {formatCurrency(costWithoutBenefits)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" color="success.main" fontWeight="600">
                      Tax savings
                    </Typography>
                    <Typography variant="body2" color="success.main" fontWeight="600">
                      -{formatCurrency(totalSavings)}
                    </Typography>
                  </Box>
                </Paper>
              </Grid>
            )}

            <Grid item xs={12}>
              <Box>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Monthly Cost Range
                </Typography>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2">
                    {formatCurrency(Math.min(...Object.values(planData.monthly_breakdown)))} -
                    {formatCurrency(Math.max(...Object.values(planData.monthly_breakdown)))}
                  </Typography>
                  <TrendingUp fontSize="small" color="action" />
                </Box>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  };

  const ChartView = () => {
    if (selectedPlans.length === 0) {
      return (
        <Alert severity="info" sx={{ mt: 3 }}>
          Select at least one plan to view charts
        </Alert>
      );
    }

    const selectedPlanData = selectedPlans.map(planId => ({
      label: healthPlans[planId].plan_name,
      data: Object.values(healthPlans[planId].monthly_breakdown),
      annualCost: healthPlans[planId].annual_cost,
    }));

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    const lineChartSeries = selectedPlanData.map((plan, index) => ({
      data: plan.data,
      label: plan.label,
      color: `hsl(${index * 137.5 % 360}, 70%, 50%)`, // Golden ratio for nice color distribution
    }));

    return (
      <Grid container spacing={4}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={3}>Monthly Cost Trends</Typography>
              <LineChart
                xAxis={[{ scaleType: 'band', data: months }]}
                series={lineChartSeries}
                height={400}
                margin={{ left: 80, right: 80, top: 40, bottom: 40 }}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={3}>Annual Cost Comparison</Typography>
              <BarChart
                xAxis={[{ scaleType: 'band', data: selectedPlanData.map(p => p.label) }]}
                series={[{
                  data: selectedPlanData.map(p => p.annualCost),
                  label: 'Annual Cost',
                  color: '#1976d2',
                }]}
                height={400}
                margin={{ left: 80, right: 80, top: 40, bottom: 40 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  if (loading) {
    return (
      <Box p={4}>
        <Skeleton variant="text" width={300} height={48} />
        <Grid container spacing={3} mt={2}>
          {[1, 2, 3].map(i => (
            <Grid item xs={12} md={4} key={i}>
              <Skeleton variant="rectangular" height={300} />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 4 }}>
        {error}
      </Alert>
    );
  }

  const bestValuePlan = getBestValue();
  const highestSavingsPlan = getHighestSavings();

  return (
    <Box sx={{ p: { xs: 2, sm: 3, md: 4 }, bgcolor: '#f8f9fa', minHeight: '100vh' }}>
      {/* Header */}
      <Box mb={4}>
        <Typography
          variant="h3"
          component="h1"
          fontWeight="700"
          color="primary"
          gutterBottom
        >
          Compare Health Plans
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" mb={3}>
          Compare costs, benefits, and savings across different health insurance plans
        </Typography>

        {/* Controls */}
        <Box display="flex" flexWrap="wrap" gap={2} alignItems="center">
          <ButtonGroup variant="outlined">
            <Button
              variant={viewMode === 'cards' ? 'contained' : 'outlined'}
              onClick={() => setViewMode('cards')}
              startIcon={<CompareArrows />}
            >
              Card View
            </Button>
            <Button
              variant={viewMode === 'chart' ? 'contained' : 'outlined'}
              onClick={() => setViewMode('chart')}
              startIcon={<TrendingUp />}
            >
              Chart View
            </Button>
          </ButtonGroup>

          <FormControlLabel
            control={
              <Switch
                checked={showTaxBenefits}
                onChange={(e) => setShowTaxBenefits(e.target.checked)}
              />
            }
            label="Show Tax Benefits"
          />

          <Chip
            label={`${selectedPlans.length} plans selected`}
            color={selectedPlans.length > 0 ? 'primary' : 'default'}
            variant="outlined"
          />
        </Box>
      </Box>

      {/* Navigation */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Button
          variant="outlined"
          onClick={() => navigateToTab(0)}
          size="large"
        >
          ← Back to Data Input
        </Button>
        
        <Button
          variant="contained"
          color="primary"
          onClick={() => navigateToTab(2)}
          size="large"
          startIcon={<Psychology />}
        >
          Get Personalized Recommendations
        </Button>
      </Box>

      {/* Content */}
      {viewMode === 'cards' ? (
        <Grid container spacing={3}>
          {getDisplayedPlans().map(([planId, planData]) => (
            <Grid item xs={12} lg={4} md={6} key={planId}>
              <PlanCard
                planId={planId}
                planData={planData}
                isSelected={selectedPlans.includes(planId)}
                isBestValue={planId === bestValuePlan}
                hasHighestSavings={planId === highestSavingsPlan}
              />
            </Grid>
          ))}
        </Grid>
      ) : (
        <ChartView />
      )}
    </Box>
  );
};

export default Compare;
