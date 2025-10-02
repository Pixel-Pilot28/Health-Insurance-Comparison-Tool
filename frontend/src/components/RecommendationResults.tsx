import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  Badge,
  Avatar,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
} from '@mui/material';
import {
  ExpandMore,
  Star,
  Warning,
  CheckCircle,
  TrendingUp,
  Shield,
  MonetizationOn,
  LocalHospital,
  CompareArrows,
  Info,
} from '@mui/icons-material';

interface RecommendationData {
  plan_id: string;
  plan_name: string;
  overall_score: number;
  score_breakdown: {
    cost_score: number;
    coverage_score: number;
    risk_score: number;
  };
  key_reasons: string[];
  warnings: string[];
  recommendation_tier: string;
  plan_details: any;
}

interface UserPreferences {
  risk_tolerance: string;
  cost_sensitivity: string;
  coverage_priority: string;
  max_monthly_premium?: number;
  max_deductible?: number;
  hsa_preference: boolean;
  family_size: number;
  age_group: string;
  health_status: string;
  preferred_network_size: string;
  travel_frequency: string;
}

interface RecommendationResultsProps {
  recommendations: RecommendationData[];
  preferences: UserPreferences | null;
  onBack: () => void;
  onReset: () => void;
}

const RecommendationResults: React.FC<RecommendationResultsProps> = ({
  recommendations,
  preferences,
  onBack,
  onReset,
}) => {
  const [expandedPlan, setExpandedPlan] = useState<string | false>(false);
  const [showComparison, setShowComparison] = useState(false);

  const handleAccordionChange = (planId: string) => (
    event: React.SyntheticEvent,
    isExpanded: boolean
  ) => {
    setExpandedPlan(isExpanded ? planId : false);
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'excellent': return 'success';
      case 'good': return 'info';
      case 'fair': return 'warning';
      case 'poor': return 'error';
      default: return 'default';
    }
  };

  const getTierIcon = (tier: string) => {
    switch (tier) {
      case 'excellent': return <Star />;
      case 'good': return <CheckCircle />;
      case 'fair': return <Info />;
      case 'poor': return <Warning />;
      default: return <Info />;
    }
  };

  const getTierLabel = (tier: string) => {
    switch (tier) {
      case 'excellent': return 'Excellent Match';
      case 'good': return 'Good Match';
      case 'fair': return 'Fair Match';
      case 'poor': return 'Poor Match';
      default: return 'Unknown';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const ScoreBar = ({ label, score, maxScore, color }: {
    label: string;
    score: number;
    maxScore: number;
    color: string;
  }) => (
    <Box mb={1}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="caption" fontWeight="600">
          {score.toFixed(1)}/{maxScore}
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={(score / maxScore) * 100}
        sx={{
          height: 6,
          borderRadius: 3,
          backgroundColor: 'grey.200',
          '& .MuiLinearProgress-bar': {
            backgroundColor: color,
            borderRadius: 3,
          },
        }}
      />
    </Box>
  );

  if (recommendations.length === 0) {
    return (
      <Alert severity="info">
        No recommendations available. Please check your preferences and try again.
      </Alert>
    );
  }

  const topRecommendation = recommendations[0];

  return (
    <Box>
      {/* Header */}
      <Box mb={4} textAlign="center">
        <Typography variant="h4" fontWeight="700" gutterBottom>
          Your Personalized Recommendations
        </Typography>
        <Typography variant="body1" color="text.secondary" mb={3}>
          Based on your preferences, we analyzed {recommendations.length} health plans. 
          Here are your best matches ranked by overall fit.
        </Typography>
        
        {/* Preference Summary */}
        <Paper elevation={1} sx={{ p: 2, display: 'inline-block' }}>
          <Box display="flex" flexWrap="wrap" gap={1} justifyContent="center">
            <Chip
              icon={<Shield />}
              label={`${preferences?.risk_tolerance} Risk`}
              size="small"
              variant="outlined"
            />
            <Chip
              icon={<MonetizationOn />}
              label={`${preferences?.cost_sensitivity} Cost Priority`}
              size="small"
              variant="outlined"
            />
            <Chip
              icon={<LocalHospital />}
              label={`${preferences?.coverage_priority} Coverage`}
              size="small"
              variant="outlined"
            />
            {preferences?.hsa_preference && (
              <Chip
                label="HSA Preferred"
                size="small"
                variant="outlined"
                color="primary"
              />
            )}
          </Box>
        </Paper>
      </Box>

      {/* Top Recommendation Highlight */}
      <Card
        elevation={3}
        sx={{
          mb: 4,
          border: '2px solid',
          borderColor: 'success.main',
          position: 'relative',
        }}
      >
        <Badge
          badgeContent="TOP PICK"
          color="success"
          sx={{
            position: 'absolute',
            top: -8,
            right: 16,
            '& .MuiBadge-badge': {
              fontSize: '0.75rem',
              height: 20,
              minWidth: 60,
            },
          }}
        />
        <CardContent sx={{ p: 3 }}>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={8}>
              <Box display="flex" alignItems="center" mb={2}>
                <Avatar
                  sx={{
                    bgcolor: 'success.main',
                    width: 48,
                    height: 48,
                    mr: 2,
                  }}
                >
                  <Star />
                </Avatar>
                <Box>
                  <Typography variant="h5" fontWeight="600">
                    {topRecommendation.plan_name}
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1} mt={0.5}>
                    <Chip
                      icon={getTierIcon(topRecommendation.recommendation_tier)}
                      label={getTierLabel(topRecommendation.recommendation_tier)}
                      color={getTierColor(topRecommendation.recommendation_tier) as any}
                      size="small"
                    />
                    <Typography variant="body2" color="text.secondary">
                      Score: {topRecommendation.overall_score.toFixed(1)}/100
                    </Typography>
                  </Box>
                </Box>
              </Box>
              
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Why this plan works for you:
                </Typography>
                <List dense>
                  {topRecommendation.key_reasons.slice(0, 3).map((reason, index) => (
                    <ListItem key={index} sx={{ py: 0.25, pl: 0 }}>
                      <ListItemIcon sx={{ minWidth: 24 }}>
                        <CheckCircle color="success" fontSize="small" />
                      </ListItemIcon>
                      <ListItemText
                        primary={reason}
                        primaryTypographyProps={{ variant: 'body2' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box textAlign="center">
                <Typography variant="h3" color="success.main" fontWeight="700">
                  {formatCurrency(topRecommendation.plan_details?.annual_cost || 0)}
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  Estimated Annual Cost
                </Typography>
                
                <Box mt={2}>
                  <ScoreBar
                    label="Cost Fit"
                    score={topRecommendation.score_breakdown.cost_score}
                    maxScore={50}
                    color="#4caf50"
                  />
                  <ScoreBar
                    label="Coverage Fit"
                    score={topRecommendation.score_breakdown.coverage_score}
                    maxScore={35}
                    color="#2196f3"
                  />
                  <ScoreBar
                    label="Risk Fit"
                    score={topRecommendation.score_breakdown.risk_score}
                    maxScore={25}
                    color="#ff9800"
                  />
                </Box>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* All Recommendations */}
      <Box mb={4}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h5" fontWeight="600">
            All Recommendations
          </Typography>
          <Button
            variant="outlined"
            startIcon={<CompareArrows />}
            onClick={() => setShowComparison(!showComparison)}
          >
            {showComparison ? 'Hide' : 'Show'} Comparison
          </Button>
        </Box>

        {recommendations.map((rec, index) => (
          <Accordion
            key={rec.plan_id}
            expanded={expandedPlan === rec.plan_id}
            onChange={handleAccordionChange(rec.plan_id)}
            sx={{ mb: 2 }}
          >
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Grid container alignItems="center" spacing={2}>
                <Grid item>
                  <Typography variant="h6" sx={{ color: 'text.primary' }}>
                    #{index + 1}
                  </Typography>
                </Grid>
                <Grid item xs>
                  <Box>
                    <Typography variant="subtitle1" fontWeight="600">
                      {rec.plan_name}
                    </Typography>
                    <Box display="flex" alignItems="center" gap={1} mt={0.5}>
                      <Chip
                        icon={getTierIcon(rec.recommendation_tier)}
                        label={getTierLabel(rec.recommendation_tier)}
                        color={getTierColor(rec.recommendation_tier) as any}
                        size="small"
                      />
                      <Typography variant="body2" color="text.secondary">
                        {rec.overall_score.toFixed(1)}/100
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item>
                  <Typography variant="h6" color="primary">
                    {formatCurrency(rec.plan_details?.annual_cost || 0)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Annual Cost
                  </Typography>
                </Grid>
              </Grid>
            </AccordionSummary>
            
            <AccordionDetails>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Why This Plan Matches Your Needs:
                  </Typography>
                  <List dense>
                    {rec.key_reasons.map((reason, idx) => (
                      <ListItem key={idx} sx={{ py: 0.25, pl: 0 }}>
                        <ListItemIcon sx={{ minWidth: 24 }}>
                          <CheckCircle color="primary" fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={reason}
                          primaryTypographyProps={{ variant: 'body2' }}
                        />
                      </ListItem>
                    ))}
                  </List>

                  {rec.warnings.length > 0 && (
                    <>
                      <Typography variant="subtitle2" color="warning.main" mt={2} mb={1}>
                        Considerations:
                      </Typography>
                      <List dense>
                        {rec.warnings.map((warning, idx) => (
                          <ListItem key={idx} sx={{ py: 0.25, pl: 0 }}>
                            <ListItemIcon sx={{ minWidth: 24 }}>
                              <Warning color="warning" fontSize="small" />
                            </ListItemIcon>
                            <ListItemText
                              primary={warning}
                              primaryTypographyProps={{ variant: 'body2' }}
                            />
                          </ListItem>
                        ))}
                      </List>
                    </>
                  )}
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Plan Details:
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">
                          Monthly Premium
                        </Typography>
                        <Typography variant="body2" fontWeight="600">
                          {formatCurrency(rec.plan_details?.premium || 0)}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">
                          Deductible
                        </Typography>
                        <Typography variant="body2" fontWeight="600">
                          {formatCurrency(rec.plan_details?.deductible || 0)}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">
                          Out-of-Pocket Max
                        </Typography>
                        <Typography variant="body2" fontWeight="600">
                          {formatCurrency(rec.plan_details?.oop_max || 0)}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">
                          Tax Savings
                        </Typography>
                        <Typography variant="body2" fontWeight="600" color="success.main">
                          {formatCurrency(rec.plan_details?.tax_savings || 0)}
                        </Typography>
                      </Grid>
                    </Grid>
                  </Paper>

                  <Box mt={2}>
                    <Typography variant="caption" color="text.secondary" mb={1} display="block">
                      Fit Score Breakdown:
                    </Typography>
                    <ScoreBar
                      label="Cost Alignment"
                      score={rec.score_breakdown.cost_score}
                      maxScore={50}
                      color="#4caf50"
                    />
                    <ScoreBar
                      label="Coverage Match"
                      score={rec.score_breakdown.coverage_score}
                      maxScore={35}
                      color="#2196f3"
                    />
                    <ScoreBar
                      label="Risk Compatibility"
                      score={rec.score_breakdown.risk_score}
                      maxScore={25}
                      color="#ff9800"
                    />
                  </Box>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>

      {/* Action Buttons */}
      <Box display="flex" gap={2} justifyContent="center" mt={4}>
        <Button variant="outlined" onClick={onBack} size="large">
          Modify Preferences
        </Button>
        <Button variant="outlined" onClick={onReset} size="large">
          Start Over
        </Button>
      </Box>
    </Box>
  );
};

export default RecommendationResults;