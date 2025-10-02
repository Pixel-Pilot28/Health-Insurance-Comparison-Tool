import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stepper,
  Step,
  StepLabel,
  Button,
  Container,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Psychology, Assessment, Recommend } from '@mui/icons-material';
import PreferencesForm from './PreferencesForm';
import RecommendationResults from './RecommendationResults';
import { getUserData } from '../api/apiClient';
import { useNavigation } from '../contexts/NavigationContext';
import axios from 'axios';

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

const steps = ['Set Preferences', 'Get Recommendations', 'Review Results'];

const Recommendations: React.FC = () => {
  const { navigateToTab } = useNavigation();
  const [activeStep, setActiveStep] = useState(0);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userData, setUserData] = useState<any>(null);

  useEffect(() => {
    // Load user data when component mounts (optional)
    const loadUserData = async () => {
      try {
        const data = await getUserData();
        if (data) {
          setUserData(data);
        } else {
          // Set default user data if none exists
          setUserData({
            userData: {
              taxRate: 25,
              planType: 'Self'
            },
            inputDetails: {
              medicalNeeds: {
                office_visits: 3,
                specialist_visits: 1,
                prescriptions: {
                  generic: 2,
                  brand: 0,
                  specialty: 0
                }
              }
            }
          });
        }
      } catch (error) {
        console.error('Failed to load user data, using defaults:', error);
        // Use default data even if API fails
        setUserData({
          userData: {
            taxRate: 25,
            planType: 'Self'
          },
          inputDetails: {
            medicalNeeds: {
              office_visits: 3,
              specialist_visits: 1,
              prescriptions: {
                generic: 2,
                brand: 0,
                specialty: 0
              }
            }
          }
        });
      }
    };

    loadUserData();
  }, []);

  const handlePreferencesSubmit = async (prefs: UserPreferences) => {
    setPreferences(prefs);
    setActiveStep(1);
    
    // Automatically generate recommendations
    await generateRecommendations(prefs);
  };

  const generateRecommendations = async (prefs: UserPreferences) => {
    if (!userData) {
      setError('User data not available. Please complete the Data Input form first.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';
      
      // First, let's debug what we're sending
      const requestData = {
        user_data: userData.userData || userData.user_data, // Handle both formats
        input_details: userData.inputDetails || userData.input_details, // Handle both formats
        preferences: prefs,
      };
      
      console.log('Sending request data:', requestData);
      
      // Try the debug endpoint first to see raw data
      try {
        const debugResponse = await axios.post(`${baseURL}/recommendations/debug-raw`, requestData);
        console.log('Debug response:', debugResponse.data);
        
        // Also try the test endpoint to see if basic structure works
        const testResponse = await axios.post(`${baseURL}/recommendations/test-generate`, requestData);
        console.log('Test endpoint response:', testResponse.data);
      } catch (debugError) {
        console.log('Debug/test endpoint error:', debugError);
      }
      
      console.log('About to call main generate endpoint:', `${baseURL}/recommendations/generate`);
      console.log('Request data being sent:', JSON.stringify(requestData, null, 2));
      
      // Try the main generate endpoint first, fall back to test endpoint if it fails
      let response;
      try {
        response = await axios.post(`${baseURL}/recommendations/generate`, requestData, {
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 30000, // 30 second timeout
        });
      } catch (generateError: any) {
        console.error('Main generate endpoint failed, trying test endpoint:', generateError);
        console.error('Error details:', {
          message: generateError.message,
          response: generateError.response?.data,
          status: generateError.response?.status,
          statusText: generateError.response?.statusText
        });
        response = await axios.post(`${baseURL}/recommendations/test-generate`, requestData, {
          headers: {
            'Content-Type': 'application/json',
          },
        });
      }

      console.log('Main generate endpoint response:', response);
      const data = response.data;
      console.log('Response data structure:', data);
      console.log('Data status:', data.status);
      console.log('Data recommendations:', data.recommendations);
      console.log('Number of recommendations:', data.recommendations ? data.recommendations.length : 'undefined');
      
      if (data.status === 'success') {
        console.log('Setting recommendations:', data.recommendations);
        setRecommendations(data.recommendations);
        setActiveStep(2);
      } else {
        console.error('Response status was not success:', data);
        throw new Error(data.message || 'Failed to generate recommendations');
      }
    } catch (error: any) {
      let errorMessage = 'Failed to generate recommendations';
      
      if (error.response) {
        // Server responded with error status
        console.error('Full server response:', error.response);
        errorMessage = `Server Error (${error.response.status}): ${error.response.data?.detail || error.response.statusText}`;
        console.error('Server response data:', error.response.data);
        console.error('Server response headers:', error.response.headers);
      } else if (error.request) {
        // Request was made but no response received
        errorMessage = 'Network Error: Unable to connect to server';
        console.error('Network error - request object:', error.request);
      } else {
        // Something else happened
        errorMessage = `Error: ${error.message}`;
        console.error('General error message:', error.message);
      }
      
      setError(errorMessage);
      console.error('Full error object:', error);
      console.error('Error stack:', error.stack);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    // Go directly back to preferences form (step 0), skipping the loading step (step 1)
    setActiveStep(0);
    // Clear any existing error state
    setError(null);
  };

  const handleReset = () => {
    setActiveStep(0);
    setPreferences(null);
    setRecommendations([]);
    setError(null);
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <PreferencesForm 
            onSubmit={handlePreferencesSubmit}
            initialValues={preferences}
          />
        );
      case 1:
        return (
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            minHeight="400px"
          >
            <CircularProgress size={60} sx={{ mb: 3 }} />
            <Typography variant="h6" gutterBottom>
              Analyzing Your Preferences
            </Typography>
            <Typography variant="body2" color="text.secondary" textAlign="center">
              We're evaluating all available health plans based on your preferences...
            </Typography>
          </Box>
        );
      case 2:
        return (
          <RecommendationResults 
            recommendations={recommendations}
            preferences={preferences}
            onBack={handleBack}
            onReset={handleReset}
          />
        );
      default:
        return <Typography>Unknown step</Typography>;
    }
  };

  // Show loading only for recommendation generation, not for initial user data
  if (!userData) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="body2" sx={{ ml: 2 }}>Loading recommendation system...</Typography>
      </Box>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box mb={4} textAlign="center">
        <Psychology sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h3" component="h1" fontWeight="700" gutterBottom>
          Personalized Plan Recommendations
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" maxWidth="600px" mx="auto">
          Get customized health insurance recommendations based on your risk tolerance, 
          budget preferences, and coverage needs
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Progress Stepper */}
      <Paper elevation={2} sx={{ p: 3, mb: 4 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {steps.map((label, index) => {
            const stepProps: { completed?: boolean } = {};
            const labelProps: { optional?: React.ReactNode } = {};

            return (
              <Step key={label} {...stepProps}>
                <StepLabel {...labelProps}>
                  <Box display="flex" alignItems="center" gap={1}>
                    {index === 0 && <Psychology fontSize="small" />}
                    {index === 1 && <Assessment fontSize="small" />}
                    {index === 2 && <Recommend fontSize="small" />}
                    {label}
                  </Box>
                </StepLabel>
              </Step>
            );
          })}
        </Stepper>
      </Paper>

      {/* Step Content */}
      <Paper elevation={1} sx={{ p: 4 }}>
        {renderStepContent(activeStep)}
      </Paper>

      {/* Main Navigation */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mt={3} mb={2}>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            onClick={() => navigateToTab(0)}
          >
            ← Data Input
          </Button>
          
          <Button
            variant="outlined"
            onClick={() => navigateToTab(1)}
          >
            ← Compare Plans
          </Button>
        </Box>
        
        {activeStep === 2 && (
          <Typography variant="body2" color="text.secondary">
            💡 Based on your preferences and data
          </Typography>
        )}
      </Box>

      {/* Step Navigation Buttons */}
      {activeStep !== 1 && !loading && (
        <Box display="flex" justifyContent="space-between" mt={3}>
          <Button
            disabled={activeStep === 0}
            onClick={handleBack}
            variant="outlined"
          >
            Back
          </Button>
          
          {activeStep === 2 && (
            <Button onClick={handleReset} variant="outlined">
              Start Over
            </Button>
          )}
        </Box>
      )}
    </Container>
  );
};

export default Recommendations;
