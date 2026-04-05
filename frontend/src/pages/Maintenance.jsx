import React, { useContext } from 'react';
import { motion } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { CheckCircle2, AlertCircle, Clock, Wrench } from 'lucide-react';
import styles from './Maintenance.module.css';

export default function Maintenance() {
  const { maintenance, language, completeMaintenanceTask, oilChangeProgramKm, setOilChangeProgram } = useContext(AppContext);
  const [resolvingId, setResolvingId] = React.useState(null);

  const containerVars = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
  const itemVars = { hidden: { x: -20, opacity: 0 }, show: { x: 0, opacity: 1 } };

  const handleComplete = async (taskId) => {
    if (resolvingId || !taskId) return;
    setResolvingId(taskId);
    try {
      await completeMaintenanceTask(taskId);
    } catch (err) {
      console.error('Failed to complete maintenance task:', err);
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <motion.div className={styles.container} variants={containerVars} initial="hidden" animate="show" exit={{ opacity: 0 }}>
      <motion.div variants={itemVars} className={styles.header}>
        <h1 className={styles.title}>{language === 'ar' ? 'الجدول الزمني للصيانة' : 'Service Timeline'}</h1>
        <div className={styles.oilPlanPanel}>
          <div className={styles.oilPlanHeader}>
            <span>{language === 'ar' ? 'خطة تغيير زيت المحرك' : 'Engine Oil Program'}</span>
          </div>
          <div className={styles.oilToggleGroup}>
            <button
              type="button"
              className={`${styles.oilToggleBtn} ${oilChangeProgramKm === '5000' ? styles.active : ''}`}
              onClick={() => setOilChangeProgram('5000')}
            >
              5,000 km
            </button>
            <button
              type="button"
              className={`${styles.oilToggleBtn} ${oilChangeProgramKm === '10000' ? styles.active : ''}`}
              onClick={() => setOilChangeProgram('10000')}
            >
              10,000 km
            </button>
          </div>
          <p className={styles.oilPlanHint}>
            {oilChangeProgramKm === '5000'
              ? (language === 'ar' ? 'التغيير الفعلي كل 5,000 كم (تنبيه 500)' : 'Effective change every 5,000 km (alert 500)')
              : (language === 'ar' ? 'التغيير الفعلي كل 10,000 كم (تنبيه 900)' : 'Effective change every 10,000 km (alert 900)')}
          </p>
        </div>
      </motion.div>

      <div className={styles.timeline}>
        {maintenance.length === 0 ? (
          <div className={styles.emptyState}>
            <CheckCircle2 size={48} color="var(--status-green)" />
            <h2>{language === 'ar' ? 'لا توجد صيانة معلقة' : 'No Pending Maintenance'}</h2>
            <p>{language === 'ar' ? 'مركبتك في حالة جيدة حالياً.' : 'Your vehicle is currently in good condition.'}</p>
          </div>
        ) : (
          maintenance.map((item, idx) => (
            <motion.div variants={itemVars} key={item.id} className={styles.timelineWrapper}>
              <div className={styles.timelineLine}>
                <div className={`${styles.timelineDot} ${styles[item.status]}`}>
                  {item.status === 'overdue' ? <AlertCircle size={16} /> : item.status === 'due-soon' ? <Clock size={16} /> : <CheckCircle2 size={16} />}
                </div>
                {idx !== maintenance.length - 1 && <div className={styles.lineTrail} />}
              </div>

              <div className={`glass-panel ${styles.itemContent}`}>
                <div className={styles.itemTop}>
                  <span className={styles.catLabel}>{item.category}</span>
                  <div className={styles.dueBadges}>
                    {item.dueInKm !== null && item.dueInKm !== undefined && (
                      <span className={`${styles.statusPill} ${styles[item.status]}`}>
                        {item.dueInKm > 0
                          ? (language === 'ar' ? `متبقي ${item.dueInKm} كم` : `${item.dueInKm} km left`)
                          : (language === 'ar' ? 'مستحق الآن' : 'Due now')}
                      </span>
                    )}
                    {item.dueInDays !== null && item.dueInDays !== undefined && (
                      <span className={`${styles.statusPill} ${styles[item.status]}`}>
                        {item.dueInDays > 0
                          ? (language === 'ar' ? `متبقي ${item.dueInDays} يوم` : `${item.dueInDays} days left`)
                          : (language === 'ar' ? 'مستحق زمنياً' : 'Time due')}
                      </span>
                    )}
                  </div>
                </div>
                <h3>{language === 'ar' ? item.titleAr : item.titleEn}</h3>
                <div className={styles.progressContainer}>
                  <div className={`${styles.progressBar} ${styles[item.status]}`} style={{ width: `${Math.min(item.progress, 100)}%` }} />
                </div>
                <div className={styles.itemActions}>
                  <button
                    type="button"
                    className={styles.resolveBtn}
                    onClick={() => handleComplete(item.id)}
                    disabled={resolvingId === item.id}
                  >
                    <Wrench size={16} />
                    <span>
                      {resolvingId === item.id
                        ? (language === 'ar' ? 'جارٍ التحديث...' : 'Updating...')
                        : (language === 'ar' ? 'تمت الصيانة' : 'Mark Completed')}
                    </span>
                  </button>
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  );
}
