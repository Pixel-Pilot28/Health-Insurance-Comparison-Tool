import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Grid,
  Chip,
  Slider,
  Alert,
  Divider,
  FormHelperText,
} from '@mui/material';
import {
  AccountBalance,
  Security,
  LocalHospital,
  Person,
  MonetizationOn,
  Psychology,
} from '@mui/icons-material';

interface PreferencesFormProps {
  onSubmit: (preferences: UserPreferences) => void;
  initialValues?: UserPreferences | null;
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

interface PreferenceOptions {
  risk_tolerance: Array<{value: string; label: string; description: string}>;
  cost_sensitivity: Array<{value: string; label: string; description: string}>;
  coverage_priority: Array<{value: string; label: string; description: string}>;
  age_groups: Array<{value: string; label: string; description: string}>;
  health_status: Array<{value: string; label: string; description: string}>;
  family_sizes: Array<{value: number; label: string}>;
}

const PreferencesForm: React.FC<PreferencesFormProps> = ({ onSubmit, initialValues }) => {
  const [preferences, setPreferences] = useState<UserPreferences>({
    risk_tolerance: initialValues?.risk_tolerance || '',
    cost_sensitivity: initialValues?.cost_sensitivity || '',
    coverage_priority: initialValues?.coverage_priority || '',
    max_monthly_premium: initialValues?.max_monthly_premium || undefined,
    max_deductible: initialValues?.max_deductible || undefined,
    hsa_preference: initialValues?.hsa_preference || false,
    family_size: initialValues?.family_size || 1,
    age_group: initialValues?.age_group || '',
    health_status: initialValues?.health_status || '',
    preferred_network_size: initialValues?.preferred_network_size || 'large',
    travel_frequency: initialValues?.travel_frequency || 'low',
  });

  const [options, setOptions] = useState<PreferenceOptions | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load preference options from API
    const loadOptions = async () => {
      try {
        const response = await fetch('/api/recommendations/options');
        const data = await response.json();
        setOptions(data);
      } catch (error) {
        console.error('Failed to load preference options:', error);
      } finally {
        setLoading(false);
      }
    };

    loadOptions();
  }, []);

  const handleInputChange = (field: keyof UserPreferences) => (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> | any
  ) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setPreferences(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleSliderChange = (field: keyof UserPreferences) => (
    event: Event,
    newValue: number | number[]
  ) => {
    setPreferences(prev => ({
      ...prev,
      [field]: Array.isArray(newValue) ? newValue[0] : newValue
    }));
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!preferences.risk_tolerance) {
      newErrors.risk_tolerance = 'Please select your risk tolerance';
    }
    if (!preferences.cost_sensitivity) {
      newErrors.cost_sensitivity = 'Please select your cost sensitivity';
    }
    if (!preferences.coverage_priority) {
      newErrors.coverage_priority = 'Please select your coverage priority';
    }
    if (!preferences.age_group) {
      newErrors.age_group = 'Please select your age group';
    }
    if (!preferences.health_status) {
      newErrors.health_status = 'Please select your health status';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    
    if (validateForm()) {
      onSubmit(preferences);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <Typography>Loading preference options...</Typography>
      </Box>
    );
  }

  if (!options) {
    return (
      <Alert severity="error">
        Failed to load preference options. Please try again.
      </Alert>
    );
  }

  const getRiskToleranceColor = (value: string) => {
    switch (value) {
      case 'conservative': return 'success';
      case 'moderate': return 'warning';
      case 'aggressive': return 'error';
      default: return 'default';
    }
  };

  const getCostSensitivityColor = (value: string) => {
    switch (value) {
      case 'very_high': return 'error';
      case 'high': return 'warning';
      case 'moderate': return 'info';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Psychology color="primary" />
        Tell Us About Your Preferences
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={4}>
        Help us understand your priorities so we can recommend the best health plans for you.
      </Typography>

      <Grid container spacing={4}>
        {/* Risk Tolerance Section */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Security color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Risk Tolerance</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" mb={3}>
                How comfortable are you with financial uncertainty in healthcare costs?
              </Typography>
              
              <FormControl fullWidth error={!!errors.risk_tolerance}>
                <Grid container spacing={2}>
                  {options.risk_tolerance.map((option) => (
                    <Grid item xs={12} md={4} key={option.value}>
                      <Card
                        sx={{
                          cursor: 'pointer',
                          border: preferences.risk_tolerance === option.value ? 2 : 1,
                          borderColor: preferences.risk_tolerance === option.value ? 'primary.main' : 'grey.300',
                          transition: 'all 0.2s',
                          '&:hover': { borderColor: 'primary.main' }
                        }}
                        onClick={() => handleInputChange('risk_tolerance')({ target: { value: option.value } })}
                      >
                        <CardContent>
                          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                            <Typography variant="subtitle1" fontWeight="600">
                              {option.label}
                            </Typography>
                            <Chip 
                              size="small" 
                              color={getRiskToleranceColor(option.value) as any}
                              variant="outlined"
                            />
                          </Box>
                          <Typography variant="body2" color="text.secondary">
                            {option.description}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
                {errors.risk_tolerance && (
                  <FormHelperText>{errors.risk_tolerance}</FormHelperText>
                )}
              </FormControl>
            </CardContent>
          </Card>
        </Grid>

        {/* Cost Sensitivity Section */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <MonetizationOn color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Cost Sensitivity</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" mb={3}>
                How important is minimizing healthcare costs in your decision?
              </Typography>
              
              <FormControl fullWidth error={!!errors.cost_sensitivity}>
                <Grid container spacing={2}>
                  {options.cost_sensitivity.map((option) => (
                    <Grid item xs={12} md={6} key={option.value}>
                      <Card
                        sx={{
                          cursor: 'pointer',
                          border: preferences.cost_sensitivity === option.value ? 2 : 1,
                          borderColor: preferences.cost_sensitivity === option.value ? 'primary.main' : 'grey.300',
                          transition: 'all 0.2s',
                          '&:hover': { borderColor: 'primary.main' }
                        }}
                        onClick={() => handleInputChange('cost_sensitivity')({ target: { value: option.value } })}
                      >
                        <CardContent>
                          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                            <Typography variant="subtitle1" fontWeight="600">
                              {option.label}
                            </Typography>
                            <Chip 
                              size="small" 
                              color={getCostSensitivityColor(option.value) as any}
                              variant="outlined"
                            />
                          </Box>
                          <Typography variant="body2" color="text.secondary">
                            {option.description}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
                {errors.cost_sensitivity && (
                  <FormHelperText>{errors.cost_sensitivity}</FormHelperText>
                )}
              </FormControl>
            </CardContent>
          </Card>
        </Grid>

        {/* Coverage Priority Section */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <LocalHospital color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Coverage Priority</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" mb={3}>
                What type of healthcare coverage is most important to you?
              </Typography>
              
              <FormControl fullWidth error={!!errors.coverage_priority}>
                <Grid container spacing={2}>
                  {options.coverage_priority.map((option) => (
                    <Grid item xs={12} md={6} key={option.value}>
                      <Card
                        sx={{
                          cursor: 'pointer',
                          border: preferences.coverage_priority === option.value ? 2 : 1,
                          borderColor: preferences.coverage_priority === option.value ? 'primary.main' : 'grey.300',
                          transition: 'all 0.2s',
                          '&:hover': { borderColor: 'primary.main' }
                        }}
                        onClick={() => handleInputChange('coverage_priority')({ target: { value: option.value } })}
                      >
                        <CardContent>
                          <Typography variant="subtitle1" fontWeight="600" mb={1}>
                            {option.label}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {option.description}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
                {errors.coverage_priority && (
                  <FormHelperText>{errors.coverage_priority}</FormHelperText>
                )}
              </FormControl>
            </CardContent>
          </Card>
        </Grid>

        {/* Personal Information Section */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Person color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Personal Information</Typography>
              </Box>
              
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth error={!!errors.age_group}>
                    <InputLabel>Age Group</InputLabel>
                    <Select
                      value={preferences.age_group}
                      onChange={handleInputChange('age_group')}
                      label="Age Group"
                    >
                      {options.age_groups.map((option) => (
                        <MenuItem key={option.value} value={option.value}>
                          {option.label}
                        </MenuItem>
                      ))}
                    </Select>
                    {errors.age_group && (
                      <FormHelperText>{errors.age_group}</FormHelperText>
                    )}
                  </FormControl>
                </Grid>

                <Grid item xs={12} md={6}>
                  <FormControl fullWidth error={!!errors.health_status}>
                    <InputLabel>Health Status</InputLabel>
                    <Select
                      value={preferences.health_status}
                      onChange={handleInputChange('health_status')}
                      label="Health Status"
                    >
                      {options.health_status.map((option) => (
                        <MenuItem key={option.value} value={option.value}>
                          {option.label}
                        </MenuItem>
                      ))}
                    </Select>
                    {errors.health_status && (
                      <FormHelperText>{errors.health_status}</FormHelperText>
                    )}
                  </FormControl>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography gutterBottom>Family Size: {preferences.family_size}</Typography>
                  <Slider
                    value={preferences.family_size}
                    onChange={handleSliderChange('family_size')}
                    min={1}
                    max={6}
                    step={1}
                    marks
                    valueLabelDisplay="auto"
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={preferences.hsa_preference}
                        onChange={handleInputChange('hsa_preference')}
                      />
                    }
                    label="Prefer HSA-eligible plans for tax benefits"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Budget Constraints */}
        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <AccountBalance color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Budget Constraints (Optional)</Typography>
              </Box>
              
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Maximum Monthly Premium"
                    value={preferences.max_monthly_premium || ''}
                    onChange={handleInputChange('max_monthly_premium')}
                    InputProps={{ startAdornment: '$' }}
                    helperText="Leave blank for no limit"
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Maximum Deductible"
                    value={preferences.max_deductible || ''}
                    onChange={handleInputChange('max_deductible')}
                    InputProps={{ startAdornment: '$' }}
                    helperText="Leave blank for no limit"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box mt={4} textAlign="center">
        <Button
          type="submit"
          variant="contained"
          size="large"
          sx={{ minWidth: 200 }}
        >
          Get My Recommendations
        </Button>
      </Box>
    </Box>
  );
};

export default PreferencesForm;