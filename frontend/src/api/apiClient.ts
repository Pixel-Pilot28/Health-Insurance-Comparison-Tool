import axios from 'axios';

// Use environment variables for base URL
const baseURL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Optional: Add an Axios interceptor for handling responses or errors globally
apiClient.interceptors.response.use(
  response => response, // success response handler
  error => {
    console.error('Error in API request:', error);
    return Promise.reject(error);
  }
);

export const fetchUserData = async () => {
  try {
    const response = await apiClient.get('/user-data');
    return response.data;
  } catch (error) {
    console.error('Error retrieving user data:', error);
    return null;
  }
};

export const fetchHealthPlans = async () => {
  try {
    const response = await apiClient.get('/health-plans');
    return response.data;
  } catch (error) {
    throw new Error("Failed to fetch health plans");
  }
};

// Function to send medical needs and user data to the backend
export const submitData = async (data: any) => {
  try {
    const response = await apiClient.post('/calculate', data);
    // const response = await apiClient.post('/user_data', data);
    // console.log('Response from backend:', response.data);
    console.log('apiClient: Raw response from backend:', JSON.stringify(response.data, null, 2));
    return response.data;
  } catch (error) {
    throw new Error("Error submitting data to backend");
  }
};

export const calculateCost = async (payload: any) => {
  try {
    const response = await apiClient.post('/calculate', payload);
    return response.data;
  } catch (error) {
    throw new Error("Error calculating costs");
  }
};

export const saveUserData = async (data: any) => {
  try {
    // Handle circular references with a replacer
    const stringifySafe = (obj: any) => {
      const seen = new WeakSet();
      return JSON.stringify(obj, (key, value) => {
        if (typeof value === "object" && value !== null) {
          if (seen.has(value)) {
            return undefined; // Ignore circular references
          }
          seen.add(value);
        }
        return value;
      });
    };

    const sanitizedData = stringifySafe(data);
    const response = await apiClient.post('/user-data', JSON.parse(sanitizedData));
    console.log('apiClient: User data saved successfully:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Error saving user data:', error.message);
    throw new Error('Failed to save user data');
  }
};

// Retrieve user data
export const getUserData = async () => {
  try {
    const response = await apiClient.get('/user-data');
    console.log('Retrieved user data:', response.data);
    return response.data;
  } catch (error: any) {
    console.error("Error fetching user data:", error.message);
    return null; // Return null if there's an error
  }
};


// Function for calculating costs
export const calculateCosts = async (payload: any) => {
  try {
    const response = await apiClient.post('/calculate', payload);
    return response.data;
  } catch (error) {
    console.error('Error calculating costs:', error);
    throw error;
  }
};

export default apiClient;

