import React, { useContext } from 'react';
import { motion } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { AlertTriangle, Wrench, ShieldCheck, Activity, ScanLine } from 'lucide-react';
import styles from './Dashboard.module.css';

export default function Dashboard() {
  const { activeVehicle, maintenance, language, setIsScanning } = useContext(AppContext);
  const nextMaintenance = maintenance.find(m => m.status === 'overdue' || m.status === 'due-soon');

  const containerVars = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };
  const itemVars = {
    hidden: { y: 20, opacity: 0 },
    show: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <motion.div 
      className={styles.container}
      variants={containerVars} initial="hidden" animate="show" exit={{ opacity: 0 }}
    >
      <motion.div variants={itemVars} className={styles.header}>
        <h1 className={styles.title}>{language === 'ar' ? 'نظرة عامة' : 'Overview'}</h1>
        <p className={styles.subtitle}>{activeVehicle.year} {activeVehicle.make} {activeVehicle.model}</p>
      </motion.div>

      {/* Main HUD Ring */}
      <motion.div variants={itemVars} className={`glass-panel ${styles.hudCard}`}>
        <div className={styles.hudRingWrap}>
          <div className={styles.hudOuterRing}>
             <motion.div 
               className={styles.hudFill}
               initial={{ background: `conic-gradient(var(--status-${activeVehicle.healthColor}) 0%, transparent 0)` }}
               animate={{ background: `conic-gradient(var(--status-${activeVehicle.healthColor}) ${activeVehicle.healthScore}%, transparent 0)` }}
               transition={{ duration: 1.5, ease: "easeOut" }}
             />
             <div className={styles.hudInner}>
                <span className={styles.hudScore}>{activeVehicle.healthScore}</span>
                <span className={styles.hudMeta}>{language === 'ar' ? 'صحة المحرك' : 'Engine Health'}</span>
             </div>
          </div>
        </div>
        
        <div className={styles.hudDetails}>
          <div className={`${styles.statusBadge} ${styles[activeVehicle.healthColor]}`}>
            {activeVehicle.healthColor === 'green' ? <ShieldCheck size={18} /> : <AlertTriangle size={18} />}
            {activeVehicle.healthStatus}
          </div>
          <p className={styles.mileage}><Activity size={16}/> {activeVehicle.mileage.toLocaleString()} km</p>
        </div>

        {/* Scan Trigger */}
        <button className={`btn-primary ${styles.scanBtn}`} onClick={() => setIsScanning(true)}>
          <ScanLine size={20} />
          {language === 'ar' ? 'بدء فحص شامل للمركبة' : 'Run Diagnostics Scan'}
        </button>

      </motion.div>

      {/* Maintenance Alert Card */}
      {nextMaintenance && (
        <motion.div variants={itemVars} className={`glass-panel ${styles.alertCard}`}>
          <div className={styles.alertIconBlock}>
             <Wrench className={styles.alertIcon} size={28} />
          </div>
          <div className={styles.alertData}>
            <h3>{language === 'ar' ? 'تنبيه صيانة' : 'Maintenance Alert'}</h3>
            <p>{language === 'ar' ? nextMaintenance.titleAr : nextMaintenance.titleEn}</p>
            <span className={`${styles.urgencyBadge} ${styles[nextMaintenance.status]}`}>
              {nextMaintenance.dueInKm > 0 ? `Due in ${nextMaintenance.dueInKm} km` : 'Action Required'}
            </span>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
