import React, { useContext, useMemo } from 'react';
import { motion } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { AlertTriangle, Wrench, ShieldCheck, Activity, ScanLine, CarFront } from 'lucide-react';
import styles from './Dashboard.module.css';

export default function Dashboard() {
  const { activeVehicle, diagnostics, maintenance, language, startScan } = useContext(AppContext);

  const healthData = useMemo(() => {
    if (!diagnostics || diagnostics.length === 0) {
      return { score: 100, color: 'green', status: language === 'ar' ? 'نموذجي' : 'Optimal Health' };
    }
    
    const latestReport = diagnostics[0]; // Assuming first is latest
    const hasHigh = latestReport.urgency === 'high';
    const hasMedium = latestReport.urgency === 'medium';
    
    if (hasHigh) return { score: 45, color: 'red', status: language === 'ar' ? 'خطر' : 'Critical Issue' };
    if (hasMedium) return { score: 72, color: 'yellow', status: language === 'ar' ? 'تنبيه' : 'Needs Inspection' };
    
    return { score: 98, color: 'green', status: language === 'ar' ? 'جيد جداً' : 'Healthy State' };
  }, [diagnostics, language]);

  const nextMaintenance = maintenance?.find(m => m.status === 'overdue' || m.status === 'due-soon');

  const containerVars = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };
  const itemVars = {
    hidden: { y: 20, opacity: 0 },
    show: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  if (!activeVehicle) {
    return (
      <div className={styles.emptyState}>
        <CarFront size={48} />
        <h2>{language === 'ar' ? 'لا توجد مركبة نشطة' : 'No Active Vehicle'}</h2>
        <p>{language === 'ar' ? 'يرجى إضافة مركبة للبدء.' : 'Please add a vehicle to get started.'}</p>
      </div>
    );
  }

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
               initial={{ background: `conic-gradient(var(--status-${healthData.color}) 0%, transparent 0)` }}
               animate={{ background: `conic-gradient(var(--status-${healthData.color}) ${healthData.score}%, transparent 0)` }}
               transition={{ duration: 1.5, ease: "easeOut" }}
             />
             <div className={styles.hudInner}>
                <span className={styles.hudScore}>{healthData.score}</span>
                <span className={styles.hudMeta}>{language === 'ar' ? 'صحة المحرك' : 'Engine Health'}</span>
             </div>
          </div>
        </div>
        
        <div className={styles.hudDetails}>
          <div className={`${styles.statusBadge} ${styles[healthData.color]}`}>
            {healthData.color === 'green' ? <ShieldCheck size={18} /> : <AlertTriangle size={18} />}
            {healthData.status}
          </div>
          <p className={styles.mileage}><Activity size={16}/> {activeVehicle.mileage.toLocaleString()} km</p>
        </div>

        {/* Scan Trigger */}
        <button className={`btn-primary ${styles.scanBtn}`} onClick={startScan}>
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
