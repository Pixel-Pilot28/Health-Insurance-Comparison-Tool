import React, { createContext, useContext, useState, ReactNode } from 'react';

interface NavigationContextType {
  currentTab: number;
  setCurrentTab: (tab: number) => void;
  navigateToTab: (tab: number) => void;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

interface NavigationProviderProps {
  children: ReactNode;
}

export const NavigationProvider: React.FC<NavigationProviderProps> = ({ children }) => {
  const [currentTab, setCurrentTab] = useState(() => {
    const savedTab = localStorage.getItem('healthPlanAppTab');
    return savedTab ? parseInt(savedTab) : 0;
  });

  const navigateToTab = (tab: number) => {
    setCurrentTab(tab);
    localStorage.setItem('healthPlanAppTab', tab.toString());
  };

  return (
    <NavigationContext.Provider value={{ currentTab, setCurrentTab, navigateToTab }}>
      {children}
    </NavigationContext.Provider>
  );
};

export const useNavigation = () => {
  const context = useContext(NavigationContext);
  if (context === undefined) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
};