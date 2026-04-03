import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { AppContext } from '../store/AppContext';
import { Scan, Settings2, Car, Calendar, GaugeCircle, Fingerprint } from 'lucide-react';
import styles from './Onboarding.module.css';

export default function Onboarding() {
  const navigate = useNavigate();
  const { mockData, language } = useContext(AppContext);
  const [mode, setMode] = useState(null); // 'auto' or 'manual'
  const [scanProgress, setScanProgress] = useState(0);

  // Manual Cascade State
  const [step, setStep] = useState(1);
  const [make, setMake] = useState('');
  const [model, setModel] = useState('');
  const [year, setYear] = useState('');
  const [vin, setVin] = useState('');
  const [mileage, setMileage] = useState('');

  const startAutoScan = () => {
    setMode('auto');
    let p = 0;
    const interval = setInterval(() => {
      p += 2;
      setScanProgress(p);
      if (p >= 100) {
        clearInterval(interval);
        /* ==============================================================
         * [BACKEND INTEGRATION: GET VEHICLE VIA BLUETOOTH]
         * If Auto-Detect succeeds, parse the OBD-II response to POST /api/vehicle/
         * ============================================================== */
        setTimeout(() => navigate('/dashboard'), 600);
      }
    }, 40);
  };

  const manualFinish = () => {
    /* ==============================================================
     * [BACKEND INTEGRATION: CREATE VEHICLE]
     * Endpoint: POST /api/vehicle/
     * Payload: { vin, make, model, year, mileage }
     * Action: Create vehicle and set the active context returned.
     * ============================================================== */
    navigate('/dashboard');
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className={styles.container}>
      <div className={styles.header}>
        <motion.div initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className={styles.logo}>
           Vehicle AI
        </motion.div>
        <p className={styles.subtitle}>{language === 'ar' ? 'التشخيص الذكي لسيارتك' : 'Premium Diagnostics Engine'}</p>
      </div>

      <AnimatePresence mode="wait">
        {!mode && (
          <motion.div key="intro" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, y: 20 }} className={styles.options}>
            <button className={`glass-panel ${styles.bigBtn}`} onClick={startAutoScan}>
              <Scan size={32} className={styles.btnIcon} />
              <div className={styles.btnText}>
                <h3>{language === 'ar' ? 'الاتصال التلقائي بـ OBD-II' : 'Auto-Detect via OBD-II'}</h3>
                <p>{language === 'ar' ? 'مسح بلوتوث آمن' : 'Secure bluetooth scanning sequence'}</p>
              </div>
            </button>
            <button className={`glass-panel ${styles.bigBtn} ${styles.secondaryLine}`} onClick={() => setMode('manual')}>
              <Settings2 size={32} className={styles.btnIcon} />
              <div className={styles.btnText}>
                <h3>{language === 'ar' ? 'إدخال يدوي' : 'Enter Details Manually'}</h3>
                <p>{language === 'ar' ? 'تحديد معلمات المركبة' : 'Select your vehicle parameters'}</p>
              </div>
            </button>
          </motion.div>
        )}

        {mode === 'auto' && (
          <motion.div key="auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={styles.scannerBox}>
            <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }} className={styles.scanRing}>
              <div className={styles.scanCore} style={{ background: `conic-gradient(var(--status-green) ${scanProgress}%, transparent 0)` }} />
            </motion.div>
            <h2 className={styles.scanData}>{scanProgress}%</h2>
            <p className={styles.scanText}>{language === 'ar' ? 'جاري الاتصال بوحدة المحرك...' : 'Interfacing with Engine Control Unit...'}</p>
          </motion.div>
        )}

        {mode === 'manual' && (
          <motion.div key="manual" initial={{ x: 30, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className={styles.manualBox}>
             
             {step === 1 && (
               <motion.div initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity:0}} className={styles.stepBlock}>
                 <label><Car size={18}/> {language === 'ar' ? 'الشركة المُصنعة' : 'Select Make'}</label>
                 <div className={styles.gridList}>
                   {mockData.brands.map(b => (
                     <button key={b} className={styles.gridItem} onClick={() => { setMake(b); setStep(2); }}>{b}</button>
                   ))}
                 </div>
               </motion.div>
             )}

             {step === 2 && (
               <motion.div initial={{opacity: 0, x: 20}} animate={{opacity: 1, x: 0}} className={styles.stepBlock}>
                 <label><Settings2 size={18}/> {language === 'ar' ? 'الموديل' : 'Select Model'}</label>
                 <div className={styles.gridList}>
                   {mockData.models[make]?.map(m => (
                     <button key={m} className={styles.gridItem} onClick={() => { setModel(m); setStep(3); }}>{m}</button>
                   ))}
                 </div>
               </motion.div>
             )}

             {step === 3 && (
               <motion.div initial={{opacity: 0, x: 20}} animate={{opacity: 1, x: 0}} className={styles.stepBlock}>
                 <label><Calendar size={18}/> {language === 'ar' ? 'سنة الصنع' : 'Select Year'}</label>
                 <div className={styles.gridList}>
                   {[2024, 2023, 2022, 2021, 2020, 2018].map(y => (
                     <button key={y} className={styles.gridItem} onClick={() => { setYear(y); setStep(4); }}>{y}</button>
                   ))}
                 </div>
               </motion.div>
             )}

             {step === 4 && (
               <motion.div initial={{opacity: 0, x: 20}} animate={{opacity: 1, x: 0}} className={styles.stepBlock}>
                 <label><Fingerprint size={18}/> {language === 'ar' ? 'رقم الهيكل (VIN)' : 'Vehicle ID Number (VIN)'}</label>
                 <input 
                   type="text" 
                   className={styles.inputField} 
                   placeholder="e.g. 1HGCM82633A..." 
                   value={vin} 
                   onChange={e => setVin(e.target.value.toUpperCase())} 
                 />
                 <button className="btn-primary" style={{ width: '100%', marginTop: 24 }} onClick={() => setStep(5)}>
                   {language === 'ar' ? 'التالي' : 'Next'}
                 </button>
               </motion.div>
             )}

             {step === 5 && (
               <motion.div initial={{opacity: 0, x: 20}} animate={{opacity: 1, x: 0}} className={styles.stepBlock}>
                 <label><GaugeCircle size={18}/> {language === 'ar' ? 'الممشى الحالي (كم)' : 'Current Mileage (km)'}</label>
                 <input 
                   type="number" 
                   className={styles.inputField} 
                   placeholder="e.g. 85000" 
                   value={mileage} 
                   onChange={e => setMileage(e.target.value)} 
                 />
                 <button className="btn-primary" style={{ width: '100%', marginTop: 24 }} onClick={manualFinish}>
                   {language === 'ar' ? 'إتمام التحليل' : 'Analyze Vehicle Details'}
                 </button>
               </motion.div>
             )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
