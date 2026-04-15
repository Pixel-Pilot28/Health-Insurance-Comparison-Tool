import React from 'react';
import { Tabs, Tab, Box, AppBar, Toolbar, Typography, Container, Paper } from '@mui/material';
import { Input, CompareArrows, Psychology, Build } from '@mui/icons-material';
import { NavigationProvider, useNavigation } from './contexts/NavigationContext';
import DataInput from './components/DataInput';
import Compare from './components/Compare';
import Recommendations from './components/Recommendations';
import OpmReconcile from './components/OpmReconcile';

const AppContent: React.FC = () => {
  const { currentTab, navigateToTab } = useNavigation();

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    navigateToTab(newValue);
  };

  const tabData = [
    {
      label: 'Data Input',
      icon: <Input />,
      description: 'Enter your personal and medical information'
    },
    {
      label: 'Compare Plans',
      icon: <CompareArrows />,
      description: 'Compare health insurance plans side-by-side'
    },
    {
      label: 'Get Recommendations',
      icon: <Psychology />,
      description: 'Get personalized plan recommendations'
    },
    {
      label: 'OPM Reconcile',
      icon: <Build />,
      description: 'Review and reconcile OPM parser results'
    }
  ];

  return (
    <Box sx={{ flexGrow: 1, bgcolor: 'background.default', minHeight: '100vh' }}>
      {/* App Header */}
      <AppBar position="static" elevation={0} sx={{ bgcolor: 'primary.main' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            Health Insurance Comparison Tool
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.9 }}>
            {tabData[currentTab].description}
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Navigation Tabs */}
      <Paper elevation={1} sx={{ borderRadius: 0 }}>
        <Container maxWidth="lg">
          <Tabs 
            value={currentTab} 
            onChange={handleChange} 
            centered
            variant="fullWidth"
            sx={{
              '& .MuiTab-root': {
                minHeight: 72,
                textTransform: 'none',
                fontSize: '1rem',
                fontWeight: 500
              }
            }}
          >
            {tabData.map((tab, index) => (
              <Tab 
                key={index}
                icon={tab.icon} 
                iconPosition="start"
                label={tab.label}
                sx={{
                  '& .MuiSvgIcon-root': {
                    fontSize: 24,
                    mr: 1
                  }
                }}
              />
            ))}
          </Tabs>
        </Container>
      </Paper>

      {/* Tab Content */}
      <Container maxWidth="lg" sx={{ mt: 3, mb: 4 }}>
        <Box>
          {currentTab === 0 && <DataInput />}
          {currentTab === 1 && <Compare />}
          {currentTab === 2 && <Recommendations />}
          {currentTab === 3 && <OpmReconcile />}
        </Box>
      </Container>
    </Box>
  );
};

function App() {
  return (
    <NavigationProvider>
      <AppContent />
    </NavigationProvider>
  );
}

export default App;
