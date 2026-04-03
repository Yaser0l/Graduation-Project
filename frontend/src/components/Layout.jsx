import React, { useContext } from 'react';
import { Outlet } from 'react-router-dom';
import { AppContext } from '../store/AppContext';
import BottomNav from './BottomNav';
import styles from './Layout.module.css';

export default function Layout() {
  const { language, toggleLanguage } = useContext(AppContext);

  return (
    <div className={styles.layout}>
      {/* Top Header Mock / Controls */}
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

      {/* Fixed Bottom Navigation */}
      <BottomNav />
    </div>
  );
}
