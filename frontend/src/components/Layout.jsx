import React, { useContext, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { LanguageContext, AuthContext } from '../store/AppContext';
import { LogOut } from 'lucide-react';
import BottomNav from './BottomNav';
import CarSwitcherSheet from './CarSwitcherSheet';
import styles from './Layout.module.css';

export default function Layout() {
  const { language, toggleLanguage } = useContext(LanguageContext);
  const { logout } = useContext(AuthContext);
  const [carsSheetOpen, setCarsSheetOpen] = useState(false);

  return (
    <div className={styles.layout}>
      {/* Top Header */}
      <header className={styles.header}>
        <div className={styles.leftSide}>
          <button className={styles.langToggle} onClick={toggleLanguage}>
            {language === 'en' ? 'عربي' : 'EN'}
          </button>
        </div>
        <div className={styles.brand}>
          {language === 'ar' ? 'سيارتيك' : 'SayyarTech'}
        </div>
        <div className={styles.rightSide}>
          <button type="button" className={styles.logoutBtn} onClick={logout}>
            <LogOut size={16} />
            <span className={styles.logoutText}>{language === 'ar' ? 'تسجيل الخروج' : 'Log Out'}</span>
          </button>
        </div>
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
