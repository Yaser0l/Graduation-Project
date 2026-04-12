import React, { useContext, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { LanguageContext, DiagnosticContext, VehicleContext } from '../store/AppContext';
import { AlertTriangle, Wrench, ShieldCheck, Activity, ScanLine, CarFront, PenLine, Check, X } from 'lucide-react';
import styles from './Dashboard.module.css';

export default function Dashboard() {
  const { activeVehicle, updateVehicleMileage } = useContext(VehicleContext);
  const { diagnostics, maintenance, startScan } = useContext(DiagnosticContext);
  const { language } = useContext(LanguageContext);
  const [isEditingMileage, setIsEditingMileage] = useState(false);
  const [mileageInput, setMileageInput] = useState('');
  const [isSavingMileage, setIsSavingMileage] = useState(false);

  const healthData = useMemo(() => {
    if (!diagnostics || diagnostics.length === 0) {
      return { score: 100, color: 'green', status: language === 'ar' ? 'نموذجي' : 'Optimal Health' };
    }

    const activeIssues = diagnostics.filter(report => !report.resolved);
    if (activeIssues.length === 0) {
      return { score: 100, color: 'green', status: language === 'ar' ? 'تم حل كل الأعطال' : 'All Issues Resolved' };
    }

    const severityBasePenalty = {
      critical: 24,
      high: 16,
      medium: 10,
      low: 5,
    };

    const totalPenalty = activeIssues.reduce((sum, report) => {
      const urgency = (report.urgency || 'medium').toLowerCase();
      const basePenalty = severityBasePenalty[urgency] ?? 8;
      const dtcCount = Array.isArray(report.dtc_codes) ? report.dtc_codes.length : 0;

      // Extra DTC penalty uses diminishing returns to avoid over-penalizing large code clusters.
      const dtcPenalty = dtcCount > 0 ? (Math.log2(dtcCount + 1) * 6) : 0;
      return sum + basePenalty + dtcPenalty;
    }, 0);

    const score = Math.max(15, Math.round(100 - totalPenalty));

    if (score <= 45) {
      return { score, color: 'red', status: language === 'ar' ? 'خطر' : 'Critical Issue' };
    }
    if (score <= 75) {
      return { score, color: 'yellow', status: language === 'ar' ? 'تنبيه' : 'Needs Inspection' };
    }

    return { score, color: 'green', status: language === 'ar' ? 'جيد جداً' : 'Healthy State' };
  }, [diagnostics, language]);

  const unresolvedDtcCount = useMemo(() => {
    if (!diagnostics?.length) return 0;
    return diagnostics
      .filter(report => !report.resolved)
      .reduce((total, report) => total + (Array.isArray(report.dtc_codes) ? report.dtc_codes.length : 0), 0);
  }, [diagnostics]);

  const pendingMaintenanceCount = useMemo(() => {
    if (!maintenance?.length) return 0;
    return maintenance.filter(task => task.status === 'overdue' || task.status === 'due-soon').length;
  }, [maintenance]);

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

  const startMileageEdit = () => {
    setMileageInput(String(activeVehicle.mileage ?? 0));
    setIsEditingMileage(true);
  };

  const cancelMileageEdit = () => {
    setIsEditingMileage(false);
    setMileageInput('');
  };

  const saveMileage = async () => {
    if (!activeVehicle || isSavingMileage) return;
    const parsed = Number(mileageInput);
    if (!Number.isFinite(parsed) || parsed < 0) return;

    setIsSavingMileage(true);
    try {
      await updateVehicleMileage(activeVehicle.id, Math.round(parsed));
      setIsEditingMileage(false);
    } catch (err) {
      console.error('Failed to update mileage:', err);
    } finally {
      setIsSavingMileage(false);
    }
  };

  return (
    <motion.div 
      className={styles.container}
      variants={containerVars} initial="hidden" animate="show" exit={{ opacity: 0 }}
    >
      <motion.div variants={itemVars} className={styles.header}>
        <div className={styles.headerTop}>
          <h1 className={styles.title}>{language === 'ar' ? 'نظرة عامة' : 'Overview'}</h1>
        </div>
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

          {!isEditingMileage ? (
            <div className={styles.mileageRow}>
              <p className={styles.mileage}><Activity size={16}/> {activeVehicle.mileage.toLocaleString()} {language === 'ar' ? 'كم' : 'km'}</p>
              <button
                type="button"
                className={styles.mileageEditBtn}
                onClick={startMileageEdit}
                title={language === 'ar' ? 'تعديل الممشى' : 'Edit mileage'}
              >
                <PenLine size={14} />
              </button>
            </div>
          ) : (
            <div className={styles.mileageEditor}>
              <input
                type="number"
                min="0"
                className={styles.mileageInput}
                value={mileageInput}
                onChange={(e) => setMileageInput(e.target.value)}
              />
              <span className={styles.mileageUnit}>{language === 'ar' ? 'كم' : 'km'}</span>
              <button
                type="button"
                className={styles.mileageActionBtn}
                onClick={saveMileage}
                disabled={isSavingMileage}
                title={language === 'ar' ? 'حفظ' : 'Save'}
              >
                <Check size={14} />
              </button>
              <button
                type="button"
                className={styles.mileageActionBtn}
                onClick={cancelMileageEdit}
                disabled={isSavingMileage}
                title={language === 'ar' ? 'إلغاء' : 'Cancel'}
              >
                <X size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Scan Trigger */}
        <button className={`btn-primary ${styles.scanBtn}`} onClick={startScan}>
          <ScanLine size={20} />
          {language === 'ar' ? 'بدء فحص شامل للمركبة' : 'Run Diagnostics Scan'}
        </button>

      </motion.div>

      <motion.div variants={itemVars} className={styles.issueGrid}>
        <div className={`glass-panel ${styles.issueCard} ${styles.dtcCard}`}>
          <div className={styles.issueCardHead}>
            <AlertTriangle size={18} />
            <h3>{language === 'ar' ? 'أعطال DTC النشطة' : 'Active DTC Issues'}</h3>
          </div>
          <p className={styles.issueCount}>{unresolvedDtcCount}</p>
          <p className={styles.issueMeta}>
            {language === 'ar'
              ? `عدد أكواد الأعطال غير المحلولة: ${unresolvedDtcCount}`
              : `${unresolvedDtcCount} unresolved DTC code${unresolvedDtcCount === 1 ? '' : 's'}`}
          </p>
        </div>

        <div className={`glass-panel ${styles.issueCard} ${styles.maintenanceCard}`}>
          <div className={styles.issueCardHead}>
            <Wrench size={18} />
            <h3>{language === 'ar' ? 'الصيانة الدورية المطلوبة' : 'Pending Maintenance Tasks'}</h3>
          </div>
          <p className={styles.issueCount}>{pendingMaintenanceCount}</p>
          <p className={styles.issueMeta}>
            {language === 'ar'
              ? `عدد مهام الصيانة المعلقة: ${pendingMaintenanceCount}`
              : `${pendingMaintenanceCount} maintenance task${pendingMaintenanceCount === 1 ? '' : 's'} due`}
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}
