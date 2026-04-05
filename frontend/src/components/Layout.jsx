import React, { useContext, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { AppContext } from '../store/AppContext';
import BottomNav from './BottomNav';
import CarSwitcherSheet from './CarSwitcherSheet';
import styles from './Layout.module.css';

export default function Layout() {
  const { language, toggleLanguage } = useContext(AppContext);
  const [carsSheetOpen, setCarsSheetOpen] = useState(false);

  return (
    <div className={styles.layout}>
      {/* Top Header */}
      <header className={styles.header}>
        <div className={styles.brand}>Vehicle AI</div>
        <button className={styles.langToggle} onClick={toggleLanguage}>
          {language === 'en' ? 'عربي' : 'EN'}
        </button>
      </header>

      {/* Main Content Area */}
      <main className={styles.main}>
        <Outlet />
      </main>

      {/* Car Switcher Bottom Sheet */}
      <CarSwitcherSheet
        isOpen={carsSheetOpen}
        onClose={() => setCarsSheetOpen(false)}
      />

      {/* Fixed Bottom Navigation */}
      <BottomNav
        onCarsOpen={() => setCarsSheetOpen(true)}
        carsSheetOpen={carsSheetOpen}
      />
    </div>
  );
}
