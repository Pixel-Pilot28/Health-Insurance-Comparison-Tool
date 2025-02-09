import React, { useEffect, useState } from 'react';
import { calculateCost } from '../api/apiClient';
import { saveUserData, submitData, fetchUserData } from '../api/apiClient'; // Ensure correct path
import {
  Box,
  Grid,
  TextField,
  Button,
  Typography,
  Autocomplete,
} from '@mui/material';

const DataInput: React.FC = () => {
  // Options for medical needs
  const medicalNeeds = [
    'Primary Care',
    'Specialist',
    'Urgent Care',
    'Emergency Care',
    'Accidental Injury',
    'Inpatient Admission',
    'Room and Board',
    'Outpatient Surgery',
    'Outpatient Tests',
    'Simple Labs',
    'Complex Labs',
    'Medications Tier 0',
    'Medications Tier 1',
    'Medications Tier 2',
    'Medications Tier 3',
    'Medications Tier 4',
    'Medications Tier 5',
    'ABA',
    'Chiropractic',
    'OT',
    'Speech Therapy',
  ];

  const [selectedNeeds, setSelectedNeeds] = useState<string[]>([]);
  const [inputDetails, setInputDetails] = useState<{ [key: string]: { count: number; dates: string[] } }>({});
  const [userData, setUserData] = useState({
    planType: '',
    income: '',
    taxRate: '',
    assumedRateOfReturn: '',
    hsa: {
      contribution: '',
      limit: '',
      percentSpent: '',
    },
    fsa: {
      contribution: '',
      limit: '',
    },
    medicare: {
      partBPremium: '',
      coveredPeople: '',
    },
  });

  // Load saved data when component mounts
  useEffect(() => {
    const fetchData = async () => {
      try {
        const savedData = await fetchUserData();
        if (savedData) {
          setUserData(savedData.userData || {});
          setInputDetails(savedData.inputDetails || {});
          setSelectedNeeds(Object.keys(savedData.inputDetails || {}));
        }
      } catch (error) {
        console.error('Error loading saved data:', error);
      }
    };
    fetchData();
  }, []);


  // Generate dates starting from January 1st of the next year
  const generateDates = (count: number): string[] => {
    const dates: string[] = [];
    const nextYear = new Date().getFullYear() + 1;
    const startDate = new Date(`${nextYear}-01-01`);
    const increment = Math.floor(365 / count);

    for (let i = 0; i < count; i++) {
      const date = new Date(startDate);
      date.setDate(startDate.getDate() + i * increment);
      dates.push(date.toISOString().split('T')[0]); // YYYY-MM-DD format
    }
    return dates;
  };

  // Handle adding new medical need inputs
  const handleAddNeed = (need: string) => {
    if (!inputDetails[need]) {
      setInputDetails({
        ...inputDetails,
        [need]: { count: 0, dates: [] },
      });
    }
  };

  // Handle count change for a medical need
  const handleCountChange = (need: string, count: number) => {
    setInputDetails({
      ...inputDetails,
      [need]: {
        count,
        dates: generateDates(count),
      },
    });
  };

  // Handle date change for a specific need and visit index
  const handleDateChange = (need: string, index: number, newDate: string) => {
    const updatedDates = [...inputDetails[need].dates];
    updatedDates[index] = newDate;
    setInputDetails({
      ...inputDetails,
      [need]: {
        ...inputDetails[need],
        dates: updatedDates,
      },
    });
  };

  const handleSubmit = async () => {
    const data = {
      userData: {
        planType: userData.planType,
        income: userData.income,
        taxRate: userData.taxRate,
        assumedRateOfReturn: userData.assumedRateOfReturn,
        hsa: { 
          contribution: userData.hsa.contribution, 
          limit: userData.hsa.limit, 
          percentSpent: userData.hsa.percentSpent 
        },
        fsa: { 
          contribution: userData.fsa.contribution, 
          limit: userData.fsa.limit 
        },
        medicare: { 
          partBPremium: userData.medicare.partBPremium, 
          coveredPeople: userData.medicare.coveredPeople 
        },
      },
      inputDetails: inputDetails,
    };
  
    console.log('Sanitized data to be submitted:', data);
  
    try {
      await saveUserData(data);
      console.log('User data sent successfully.');
    } catch (error: any) {
      console.error('Error sending user data:', error.message);
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Enter Your Data
      </Typography>

      {/* User Data Section */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label=""
            select
            value={userData.planType}
            onChange={(e) => setUserData({ ...userData, planType: e.target.value })}
            SelectProps={{ native: true }}
          >
            <option value="">Select</option>
            <option value="Self">Self</option>
            <option value="Self + Family">Self + Family</option>
            <option value="Self + One">Self + One</option>
          </TextField>
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="Income ($)"
            type="number"
            value={userData.income}
            onChange={(e) => setUserData({ ...userData, income: e.target.value })}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="Effective Tax Rate (%)"
            type="number"
            value={userData.taxRate}
            onChange={(e) => setUserData({ ...userData, taxRate: e.target.value })}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="Assumed Rate of Return (%)"
            type="number"
            value={userData.assumedRateOfReturn}
            onChange={(e) => setUserData({ ...userData, assumedRateOfReturn: e.target.value })}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="HSA Contribution ($)"
            type="number"
            value={userData.hsa.contribution}
            onChange={(e) => setUserData({
              ...userData,
              hsa: { ...userData.hsa, contribution: e.target.value },
            })}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="HSA Limit ($)"
            type="number"
            value={userData.hsa.limit}
            onChange={(e) => setUserData({
              ...userData,
              hsa: { ...userData.hsa, limit: e.target.value },
            })}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="Percent of HSA Spent Per Year (%)"
            type="number"
            value={userData.hsa.percentSpent}
            onChange={(e) => setUserData({
              ...userData,
              hsa: { ...userData.hsa, percentSpent: e.target.value },
            })}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="FSA Contribution ($)"
            type="number"
            value={userData.fsa.contribution}
            onChange={(e) => setUserData({
              ...userData,
              fsa: { ...userData.fsa, contribution: e.target.value },
            })}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="FSA Limit ($)"
            type="number"
            value={userData.fsa.limit}
            onChange={(e) => setUserData({
              ...userData,
              fsa: { ...userData.fsa, limit: e.target.value },
            })}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="Medicare Part B Premium Cost"
            type="number"
            value={userData.medicare.partBPremium}
            onChange={(e) => setUserData({
              ...userData,
              medicare: { ...userData.medicare, partBPremium: e.target.value },
            })}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            label="People Covered Under Parts A/B"
            type="number"
            value={userData.medicare.coveredPeople}
            onChange={(e) => setUserData({
              ...userData,
              medicare: { ...userData.medicare, coveredPeople: e.target.value },
            })}
          />
        </Grid>
      </Grid>

      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Enter Your Medical Needs
      </Typography>

      {/* Dropdown for selecting medical needs */}
      <Autocomplete
        multiple
        options={medicalNeeds}
        value={selectedNeeds}
        onChange={(event, newValue) => {
          setSelectedNeeds(newValue);
          newValue.forEach((need) => handleAddNeed(need));
        }}
        renderInput={(params) => (
          <TextField {...params} label="Select Medical Needs" variant="outlined" />
        )}
      />

      <Box sx={{ mt: 4 }}>
        {/* Render input fields for selected needs */}
        {selectedNeeds.map((need) => (
          <Box key={need} sx={{ mb: 4 }}>
            <Typography variant="h6" gutterBottom>
              {need}
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label={`Number of ${need} visits/refills`}
                  type="number"
                  value={inputDetails[need]?.count || 0}
                  onChange={(e) => handleCountChange(need, Number(e.target.value))}
                />
              </Grid>
            </Grid>
            <Grid container spacing={2} sx={{ mt: 2, pl: 2 }}>
              {inputDetails[need]?.dates.map((date, index) => (
                <Grid item xs={12} md={6} key={index}>
                  <TextField
                    fullWidth
                    label={`Date for ${need} #${index + 1}`}
                    type="date"
                    value={date}
                    onChange={(e) => handleDateChange(need, index, e.target.value)}
                  />
                </Grid>
              ))}
            </Grid>
          </Box>
        ))}

        <Button
          variant="contained"
          color="primary"
          //onClick={() => console.log('Submitted Data:', { userData, inputDetails })} //Use for debug
          onClick={handleSubmit}
        >
          Save & Submit
        </Button>
      </Box>
    </Box>
  );
};

export default DataInput;   