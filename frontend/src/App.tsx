import React from 'react';
import { Tabs, Tab, Box } from '@mui/material';
import DataInput from './components/DataInput';
import Compare from './components/Compare';
import Recommendations from './components/Recommendations';

function App() {
  const [currentTab, setCurrentTab] = React.useState(0);

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  return (
    <Box>
      <Tabs value={currentTab} onChange={handleChange} centered>
        <Tab label="Data Input" />
        <Tab label="Compare" />
        <Tab label="Recommendations" />
      </Tabs>
      <Box sx={{ padding: 3 }}>
        {currentTab === 0 && <DataInput />}
        {currentTab === 1 && <Compare />}
        {currentTab === 2 && <Recommendations />}
      </Box>
    </Box>
  );
}

export default App;
