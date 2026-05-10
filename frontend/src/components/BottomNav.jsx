import React, { useContext } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Stethoscope, Wrench, MessageSquareText } from 'lucide-react';
import clsx from 'clsx';
import styles from './BottomNav.module.css';
import { AppContext } from '../store/AppContext';

export default function BottomNav() {
  const { language } = useContext(AppContext);

  const navItems = [
    { to: "/dashboard", icon: LayoutDashboard, labelEn: "Dashboard", labelAr: "الرئيسية" },
    { to: "/diagnostics", icon: Stethoscope, labelEn: "Diagnostics", labelAr: "التشخيص" },
    { to: "/maintenance", icon: Wrench, labelEn: "Maintenance", labelAr: "الصيانة" },
    { to: "/chat", icon: MessageSquareText, labelEn: "AI Chat", labelAr: "المساعد" },
  ];

  return (
    <nav className={styles.bottomNav}>
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
