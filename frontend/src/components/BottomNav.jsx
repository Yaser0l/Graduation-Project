import React, { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Stethoscope, Wrench, CarFront } from 'lucide-react';
import clsx from 'clsx';
import styles from './BottomNav.module.css';
import { LanguageContext } from '../store/AppContext';

export default function BottomNav({ onCarsOpen, carsSheetOpen }) {
  const { language } = useContext(LanguageContext);

  const navItems = [
    { to: "/dashboard", icon: LayoutDashboard, labelEn: "Dashboard", labelAr: "الرئيسية" },
    { to: "/diagnostics", icon: Stethoscope, labelEn: "Diagnostics", labelAr: "التشخيص" },
    { to: "/maintenance", icon: Wrench, labelEn: "Maintenance", labelAr: "الصيانة" },
  ];

  return (
    <nav className={styles.bottomNav}>
      {/* My Cars tab — leftmost */}
      <button
        className={clsx(styles.navItem, styles.carsBtn, carsSheetOpen && styles.active)}
        onClick={onCarsOpen}
      >
        <CarFront className={styles.icon} size={24} strokeWidth={2} />
        <span className={styles.label}>
          {language === 'ar' ? 'سياراتي' : 'My Cars'}
        </span>
      </button>

      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => clsx(styles.navItem, isActive && styles.active)}
        >
          <item.icon className={styles.icon} size={24} strokeWidth={2} />
          <span className={styles.label}>
            {language === 'ar' ? item.labelAr : item.labelEn}
          </span>
        </NavLink>
      ))}
    </nav>
  );
}
