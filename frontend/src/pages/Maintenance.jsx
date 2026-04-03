import React, { useContext } from 'react';
import { motion } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import styles from './Maintenance.module.css';

export default function Maintenance() {
  const { maintenance, language } = useContext(AppContext);

  const containerVars = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
  const itemVars = { hidden: { x: -20, opacity: 0 }, show: { x: 0, opacity: 1 } };

  return (
    <motion.div className={styles.container} variants={containerVars} initial="hidden" animate="show" exit={{ opacity: 0 }}>
      <motion.div variants={itemVars} className={styles.header}>
        <h1 className={styles.title}>{language === 'ar' ? 'الجدول الزمني للصيانة' : 'Service Timeline'}</h1>
      </motion.div>
      
      <div className={styles.timeline}>
        {maintenance.map((item, idx) => (
          <motion.div variants={itemVars} key={item.id} className={styles.timelineWrapper}>
            <div className={styles.timelineLine}>
              <div className={`${styles.timelineDot} ${styles[item.status]}`}>
                 {item.status === 'overdue' ? <AlertCircle size={16}/> : item.status === 'due-soon' ? <Clock size={16}/> : <CheckCircle2 size={16}/>}
              </div>
              {idx !== maintenance.length - 1 && <div className={styles.lineTrail} />}
            </div>
            
            <div className={`glass-panel ${styles.itemContent}`}>
              <div className={styles.itemTop}>
                <span className={styles.catLabel}>{item.category}</span>
                <span className={`${styles.statusPill} ${styles[item.status]}`}>
                  {item.dueInKm > 0 ? `${item.dueInKm} km` : (language === 'ar' ? 'متأخر' : 'Overdue')}
                </span>
              </div>
              <h3>{language === 'ar' ? item.titleAr : item.titleEn}</h3>
              <div className={styles.progressContainer}>
                <div className={`${styles.progressBar} ${styles[item.status]}`} style={{ width: `${Math.min(item.progress, 100)}%` }} />
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
